import sqlite3
from flask import Flask, render_template, request, Response, jsonify

# from flask_sqlalchemy import SQLAlchemy
# from datatables import ColumnDT, DataTables

import time
import datetime
import sys
sys.path.append('../API/')
sys.path.append('../Ratings')
sys.path.append('./Ratings')
import rating as rt
import json
import os.path
from math import ceil
import configparser

app = Flask(__name__)





if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Use command 'python app.py sitecfg.ini'")
        param_fname = "sitecfg.ini"
    else:
        param_fname = sys.argv[1]

    print(param_fname)
    
    config = configparser.ConfigParser()
    config.read(param_fname)    
    
    data_db = config['DATABASES']['data_db']
    rating_db = config['DATABASES']['ratings_db']
    
    website_url = config['SITE']['domain']
    port = int(config['SITE']['port'])
 
    subdomain = config['SITE']['subdomain']

    print(website_url)
    app.config['SERVER_NAME'] = website_url
    

# subdomain = "rating3"

def get_db_connection(factory = True):
    # conn = sqlite3.connect('file:Output/rating_for_site.db?immutable=1', uri=True)
    conn = sqlite3.connect(f'file:{rating_db}?immutable=1', uri=True)
    conn.execute("ATTACH DATABASE ? AS data;", (data_db,))
    if factory:
        conn.row_factory = sqlite3.Row
    return conn


# @app.route('/', subdomain=subdomain)
# def ratingindex():
#     return "secret rating page"



@app.route('/')
def index():
    return "Hello World"

@app.route('/about')
def about():
    return "About page"

@app.route('/druzhba', subdomain=subdomain)
def showDruzhba():
    return render_template("druzhba50.html")

@app.route('/druzhba2025', subdomain=subdomain)
def showDruzhba2025():
    return render_template("druzhba2025.html")


@app.route('/players2', subdomain=subdomain)
@app.route("/players2/<int:season>", subdomain=subdomain)
def showAllPlayersDT(season = 0):
    return render_template("allplayersDT.html", ratings=[], page = 0)




@app.route('/players', subdomain=subdomain)
@app.route("/players/<int:season>", subdomain=subdomain)
def showAllPlayers(season = 0):
    page = request.args.get('page', 1, type=int)
    ts = time.time()
    conn = get_db_connection()
    if season == 0:
        tmp = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratings').fetchall()
        season = int(tmp[0]["releaseid"])
    t1 = time.time()
    print(page, t1-ts)
    ratings = conn.execute('SELECT ROW_NUMBER() OVER(ORDER BY playerratings.playerrating DESC) AS position, players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN data.players as players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN data.players as players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, pr.playerrating as playerrating, pr.releaseid as releaseid FROM (SELECT * FROM playerratings WHERE releaseid='+str(season)+' ORDER BY playerrating DESC LIMIT 500) as pr JOIN data.players as players ON pr.playerid=players.playerid ORDER BY pr.playerrating DESC LIMIT 500').fetchall()
    #players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid
    # ratings["position"] = [x+1+(page-1)*500 for x in range(len(ratings))]
    t2= time.time()
    print(t2 - t1, len(ratings))
    conn.close()
    return render_template("allplayers.html", ratings=ratings, page = page)

@app.route('/api/byauthor/<int:authorid>/<int:playerid>', subdomain=subdomain)
def AuthorPlayerStats(authorid, playerid, return_json = True):
    print(authorid, playerid)
    conn = get_db_connection()
    conn.execute("ATTACH DATABASE 'Output/authors.db' as authors")
    player_data = conn.execute("SELECT a.tournamentid, a.questionid, a.gqid, r.teamid, teamrating, hardnes, d.teamname, d.mask, tr.name FROM authors.questions AS a INNER JOIN questionrating as q ON a.authorid == ? AND a.tournamentid==q.tournamentid AND a.questionid==q.questionid " +
                               "INNER JOIN data.roster as r ON r.playerid = ? AND a.tournamentid == r.tournamentid " +
                                "INNER JOIN tournamentratings as t ON r.tournamentid==t.tournamentid AND r.teamid==t.teamid "+
                                "INNER JOIN data.results as d ON r.tournamentid==d.tournamentid AND r.teamid==d.teamid "+
                                "INNER JOIN data.tournaments as tr on tr.tournamentid==d.tournamentid", (authorid, playerid,))
                               
                               
                               
                            #    , (authorid, playerid))#\
    # player_data = conn.execute("SELECT * FROM questionrating as q ")#\
                                # a.tournamentid, a.questionid, q.hardnes"\
                                #, r.playerid, t.teamrating  " \
                                # "FROM authors.questions as a INNER JOIN questionrating as q ON a.authorid = ? AND a.tournamentid==q.tournamentid AND a.questionid == q.questionid " \
                                # "", (authorid,))
    #                             "INNER JOIN data.roster as r ON r.playerid = ? AND a.tournamentid == r.tournamentid " \
    #                             "INNER JOIN tournamentratings as t ON r.tournamentid==t.tournamentid AND r.teamid==t.teamid", (authorid, playerid,))
    if return_json:
        return json.dumps([dict(x) for x in player_data], ensure_ascii=True)
    else:
        return [x for x in player_data]

@app.route('/funstat/player_by_author/<int:authorid>/<int:playerid>', subdomain=subdomain)
def AuthorPlayerStatsHTML(authorid, playerid):
    data = AuthorPlayerStats(authorid, playerid, False)
    by_tournaments = {}
    played = len(data)
    for v in data:
        # print(dict(v))

        if not v["tournamentid"] in by_tournaments:
            by_tournaments[v["tournamentid"]] = {"id": v["tournamentid"], "name": v["name"], "teamname": v["teamname"],"teamid": v["teamid"], "teamrating":v["teamrating"], "questions":[], "got":0, "estimation":0}
        by_tournaments[v["tournamentid"]]["questions"].append({"qid": v["questionid"], "got": v["mask"][v["questionid"]-1] if len(v["mask"]) >= v["questionid"] else "U", "hardnes": v["hardnes"], "chance":rt.ELO(v["teamrating"], v["hardnes"]), "gqid":v["gqid"]})
        by_tournaments[v["tournamentid"]]["got"] += (v["mask"][v["questionid"]-1] == "1" if len(v["mask"]) >= v["questionid"] else 0)
        by_tournaments[v["tournamentid"]]["estimation"] += rt.ELO(v["teamrating"], v["hardnes"])
    return render_template("playerauthorstat.html", by_tournaments=by_tournaments, played = played)




@app.route('/api/questions/<int:tournamentid>', subdomain=subdomain)
def QuestionsHardnes(tournamentid, return_json = True):
    conn = get_db_connection()
    questions = conn.execute(f'SELECT hardnes FROM questionrating WHERE tournamentid == {tournamentid}').fetchall()
    if return_json:
        return json.dumps([x['hardnes'] for x in questions], ensure_ascii=True)
    else:
        return [x['hardnes'] for x in questions]


@app.route('/api/players', subdomain=subdomain)
def PlayersData():
    ts = time.time()
    conn = get_db_connection()
    # page = request.args.get('page', 1, type=int)
    # ts = time.time()
    # conn = get_db_connection()
    # if season == 0:
    tmp = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratings').fetchall()
    season = int(tmp[0]["releaseid"])
    # t1 = time.time()
    # print(page, t1-ts)
    ratings = conn.execute('SELECT playerratings.place AS position, players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as rating, playerratings.releaseid as releaseid FROM playerratings JOIN data.players as players ON playerratings.playerid=players.playerid WHERE playerratings.releaseid='+str(season) + ' ORDER BY playerratings.releaseid DESC, playerratings.playerrating DESC ')
    t1 = time.time()
    print(t1-ts)
    res = json.dumps({"data":[dict(x) for x in ratings]})
    t2 = time.time()
    print(t2-t1)
    return res
    # 'LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()



    # conn = get_db_connection()
    # ratings = conn.execute('SELECT releaseid, playerrating FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC')
    # return json.dumps({x["releaseid"]:x["playerrating"] for x in ratings})


@app.route('/api/player/<int:playerid>', subdomain=subdomain)
def PlayerRates(playerid):
    conn = get_db_connection()
    ratings = conn.execute('SELECT releaseid, playerrating FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC')
    return json.dumps({x["releaseid"]:x["playerrating"] for x in ratings})

@app.route('/api/tournamentteamresult/<int:tournamentid>/<int:teamid>', subdomain=subdomain)
def TeamResult(tournamentid, teamid):
    conn = get_db_connection()
    res = conn.execute(f'SELECT * FROM data.results WHERE tournamentid = {tournamentid} and teamid = {teamid}').fetchone()
    if res is None:
        return {}
    return json.dumps(dict(res))

@app.route('/api/tournamentteamrates/<int:tournamentid>/<int:teamid>', subdomain=subdomain)
def TeamRates(tournamentid, teamid):
    conn = get_db_connection()
    res = conn.execute(f'SELECT * FROM tournamentratings WHERE tournamentid = {tournamentid} and teamid = {teamid}').fetchone()
    if res is None:
        return {}
    return json.dumps(dict(res))

@app.route('/api/tournamentteamrates/<int:tournamentid>', subdomain=subdomain)
def AllTeamRates(tournamentid):
    conn = get_db_connection()
    res = conn.execute(f'SELECT * FROM tournamentratings WHERE tournamentid = {tournamentid}')
    if res is None:
        return {}
    return json.dumps([dict(r) for r in res])

@app.route("/api/tournament_full/<int:tournamentid>", subdomain=subdomain)
def apiFullTournamentFullInfo(tournamentid):
    conn = get_db_connection()
    tournaments_r = conn.execute('SELECT * FROM data.results as results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' +  
    ' WHERE results.tournamentid = '+str(tournamentid) + ";"#+
    # ' ORDER BY place'
    )
    tournaments = [dict(x) for x in tournaments_r]
    
    tournament_info = dict(conn.execute('SELECT * FROM data.tournaments as tournaments  WHERE tournamentid = '+str(tournamentid)).fetchone())

    tours_number_info = conn.execute('SELECT max(leg) FROM tournaments_legs WHERE tournaments_legs.tournamentid = ' +str(tournamentid)).fetchall()
    tours_number = 0
    if len(tours_number_info) >0:
        if not tours_number_info[0][0] is None:
            tours_number = tours_number_info[0][0]

    leg_info = conn.execute('SELECT teamid, leg, legquestions, predictedquestions FROM tournaments_legs WHERE tournaments_legs.tournamentid = ' +str(tournamentid)).fetchall()
    leg_dict = {}
    for l in leg_info:
        if not l["teamid"] in leg_dict:
            leg_dict[l["teamid"]] = {}
        leg_dict[l["teamid"]][l["leg"]] = {"predict":l["predictedquestions"], "get":l["legquestions"]}
    
    conn.close()

    all_data = dict(tourresults=tournaments, tournamentid = tournamentid, tournament_info = tournament_info, tours_number=tours_number, leg_dict = leg_dict)

    return json.dumps(all_data)




@app.route('/teamshow/<int:tournamentid>/<int:teamid>', subdomain=subdomain)
def TeamShow(tournamentid, teamid):
    return render_template("teamshow.html", tournamentid=tournamentid, teamid = teamid)



@app.route('/api/calculate', subdomain=subdomain)
def Calculate():
    #base parameters for calculate:
    #teams -- list of lists of players id
    #

    teams = None
    teams_info = request.args.get('teams')
    if not teams_info is None:
        teams = json.loads(teams_info)
    
    tournamets = request.args.get('tournaments')
    tournametsid = None
    if not tournamets is None:
        tournametsid = json.loads(tournamets)
    
    release = request.args.get('release')
    if release is None:
        release = rt.season_by_datetime(datetime.datetime.today())
    release = int(release)
    result = []
    
    used_rates = []
    team_rates = []
    if not teams is None: 
        for t in teams:
            used_rates.append([])
            for plid in t:
                used_rates[-1].append(PlayerRatesRelease(plid, release, False))
            team_rates.append(rt.independed_ELO(sorted(used_rates[-1], reverse=True)[:6]))
            result.append({"PlayerRates":used_rates[-1], "TeamRating":team_rates[-1]})
    team_gets = None

    if not tournametsid is None:
        team_gets = [[0]*len(tournametsid) for x in  range(len(team_rates))]

        for i, tid in enumerate(tournametsid):
            qh = QuestionsHardnes(tid, False)
            if len(qh) > 0:
                for j, rate in enumerate(team_rates):
                    team_gets[j][i] = rt.ELO_estimate(rate, qh)
    
        for j, rate in enumerate(team_rates):
            result[j]["TeamEstimates"] = team_gets[j]

    return json.dumps(result)


@app.route('/api/player/<int:playerid>/full', subdomain=subdomain)
def PlayerDetailedRates(playerid, return_json = True):
    conn = get_db_connection()
    ts = time.time()
    # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # deltas_cursor = conn.execute('SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid, totalquestions FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN results ON playerratingsdelta.tournamentid=results.tournamentid AND playerratingsdelta.teamid=results.teamid')# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # deltas_cursor2 = conn.execute('SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, playerratingsdelta.teamid as teamid, teamrating, predictedquestions, teamperformance FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN tournamentratings ON playerratingsdelta.tournamentid=tournamentratings.tournamentid AND playerratingsdelta.teamid=tournamentratings.teamid')# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
   
    deltas_cursor = conn.execute('SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid, teamrating, predictedquestions, teamperformance, totalquestions FROM (playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN data.results as results ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=results.tournamentid AND playerratingsdelta.teamid=results.teamid) JOIN tournamentratings ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=tournamentratings.tournamentid AND playerratingsdelta.teamid=tournamentratings.teamid')# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    
    
    # deltas_cursor = conn.execute('SELECT pd.tournamentid as tournamentid, releaseid, deltarating, teamname, name, pd.teamid as teamid, teamrating, predictedquestions, teamperformance, totalquestions FROM (SELECT * from playerratingsdelta WHERE playerid =  '+str(playerid) +') as pd JOIN data.tournaments as tournaments ON pd.tournamentid=tournaments.tournamentid JOIN data.results as results ON pd.tournamentid=results.tournamentid AND pd.teamid=results.teamid JOIN tournamentratings ON pd.tournamentid=tournamentratings.tournamentid AND pd.teamid=tournamentratings.teamid')# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    
    
    # deltas_cursor = conn.execute('SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid, teamrating, predictedquestions, teamperformance FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN tournamentratings ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=tournamentratings.tournamentid AND playerratingsdelta.teamid=tournamentratings.teamid')# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
   
   
    # smth = conn.execute('EXPLAIN SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid, teamrating, predictedquestions, teamperformance, totalquestions FROM (playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN data.results as results ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=results.tournamentid AND playerratingsdelta.teamid=results.teamid) JOIN tournamentratings ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=tournamentratings.tournamentid AND playerratingsdelta.teamid=tournamentratings.teamid')# ORDER BY playerratingsdelta.releaseid DESC').fetchall()

    # smth = conn.execute('EXPLAIN SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid, teamrating, predictedquestions, teamperformance, totalquestions FROM (playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN results ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=results.tournamentid AND playerratingsdelta.teamid=results.teamid) JOIN tournamentratings ON playerratingsdelta.playerid = '+str(playerid) + ' AND playerratingsdelta.tournamentid=tournamentratings.tournamentid AND playerratingsdelta.teamid=tournamentratings.teamid')
    # print([dict(x) for x in smth])
    # # print([x["releaseid"] for x in deltas]  )
    ts11 = time.time()
    
    deltas = [dict(x) for x in deltas_cursor]
    deltas.sort(key=lambda x: -x["releaseid"])
    # deltas = []
    ts1 = time.time()
    print(f"gather tournaments info {(ts1-ts):0.2f}({(ts11-ts):0.2f}) sec")
    # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.tournamentid=tournaments.tournamentid JOIN roster ON tournaments.tournamentid=roster.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    ratings_cursor = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC')
    ratings = [dict(x) for x in ratings_cursor]
    ts2 = time.time()
    print(f"collect ratings {(ts2-ts1):0.2f}")  
    print(f"total prepare {(ts2-ts):0.2f}")  
    player = conn.execute('SELECT * FROM players WHERE playerid = '+str(playerid)).fetchone()

    if player is None:
        playerinfo = {"playerid":playerid, "name":"", "surname":"", "patronim":"", "fullname":"Игрок "+str(playerid)}
    else:
        playerinfo = dict(player)


    if return_json:
        return json.dumps({"deltas":deltas, "rates":ratings, "player":playerinfo}, ensure_ascii=True)
    else:
        return (deltas, ratings, player)
        


@app.route('/api/player/<int:playerid>/last', subdomain=subdomain)
def PlayerRatesLast(playerid, return_json = True):
    conn = get_db_connection()
    ratings = conn.execute('SELECT releaseid, playerrating FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchone()
    if not ratings is None:
        if return_json:
            return json.dumps(ratings["playerrating"])
        else:
            return ratings["playerrating"]
    else:
        if return_json:
            return json.dumps(1000)
        else:
            return 1000

@app.route('/api/player/<int:playerid>/<int:releaseid>', subdomain=subdomain)
def PlayerRatesRelease(playerid, releaseid, return_json = True):
    result = None
    conn = get_db_connection()
    ratings = conn.execute('SELECT releaseid, playerrating FROM playerratings WHERE playerid = '+str(playerid)+' AND releaseid = '+ str(releaseid) +' ORDER BY releaseid DESC').fetchall()
    if len(ratings) == 0:
        mm_releases = conn.execute('SELECT releaseid, playerrating FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
        if len(mm_releases) == 0:
            result = 1000
        elif releaseid > mm_releases[0]["releaseid"]:
            result = mm_releases[0]["playerrating"]
        else:
            result = 1000
    else:
        result = ratings[0]["playerrating"]
    if return_json:
        return json.dumps(result)
    return(result)


@app.route('/', subdomain=subdomain)
@app.route('/teams', subdomain=subdomain)
def showAllTeams(season = 0):
    page = request.args.get('page', 1, type=int)
    ts = time.time()
    conn = get_db_connection()
    if season == 0:
        tmp = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratings').fetchall()
        season = int(tmp[0]["releaseid"])
    t1 = time.time()
    print(page, t1-ts)
    ratings = conn.execute('SELECT ROW_NUMBER() OVER(ORDER BY teambaseratings.teambaserating DESC) AS position, teams.teamid as teamid, teams.teamname as name, teambaseratings.teambaserating as teamrating, teambaseratings.releaseid as releaseid FROM teambaseratings JOIN data.teams as teams ON teambaseratings.teamid=teams.teamid WHERE releaseid='+str(season)+' ORDER BY teamrating DESC LIMIT 100 OFFSET '+str(100*(page-1))).fetchall()
    # ratings = conn.execute('SELECT ROW_NUMBER() OVER(ORDER BY playerratings.playerrating DESC) AS position, players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN data.players as players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN data.players as players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, pr.playerrating as playerrating, pr.releaseid as releaseid FROM (SELECT * FROM playerratings WHERE releaseid='+str(season)+' ORDER BY playerrating DESC LIMIT 500) as pr JOIN data.players as players ON pr.playerid=players.playerid ORDER BY pr.playerrating DESC LIMIT 500').fetchall()
    #players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid
    # ratings["position"] = [x+1+(page-1)*500 for x in range(len(ratings))]
    t2= time.time()
    print(t2 - t1, len(ratings))
    conn.close()
    return render_template("allteams.html", ratings=ratings, page = page)





@app.route("/player/<int:playerid>", subdomain=subdomain)
def showPlayerInfo(playerid):
    conn = get_db_connection()
    ts = time.time()
    # # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # deltas = conn.execute('SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN results ON playerratingsdelta.tournamentid=results.tournamentid AND playerratingsdelta.teamid=results.teamid').fetchall()# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # # print([x["releaseid"] for x in deltas]  )
    # deltas.sort(key=lambda x: -x["releaseid"])
    
    # ts1 = time.time()
    # # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN  data.tournaments as tournaments  ON playerratingsdelta.tournamentid=tournaments.tournamentid JOIN roster ON tournaments.tournamentid=roster.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
    # # ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)).fetchall()
    # ts2 = time.time()

    
    playername_req = conn.execute('SELECT fullname from players WHERE playerid='+str(playerid)).fetchone()
    if playername_req is None:
        playername = "Нет данных"
    else:
        playername = playername_req["fullname"]
    conn.close()
    deltas, ratings, playerinfo = PlayerDetailedRates(playerid, False)
    # print("deltas", ts1 - ts, "ratings", ts2-ts1)
    rate_list = []
    deltas_idx = 0
    for r in ratings:
        # print(dict(r))
        rate_list.append({"releaseid":r["releaseid"],"releasename":rt.season_to_date_string(r["releaseid"]), "tournaments_count":0, "tournaments_details":[], "place": r["place"], "rating": r["playerrating"]})
        while deltas_idx < len(deltas):
            if rate_list[-1]["releaseid"] == deltas[deltas_idx]["releaseid"]:
                rate_list[-1]["tournaments_count"] += 1
                rate_list[-1]["tournaments_details"].append(deltas[deltas_idx])
                deltas_idx += 1
            else:
                break

    ts1 = time.time()
    print(f"player {playerid} data prepare {(ts1-ts):0.2f}")
    return render_template("player.html", ratings=rate_list, playerid=playerid, playername=playername)


@app.route("/robots.txt", subdomain=subdomain)
def noindex():
    r = Response(response="User-Agent: *\nDisallow: /\n", status=200, mimetype="text/plain")
    r.headers["Content-Type"] = "text/plain; charset=utf-8"
    return r

@app.route("/compareplayers", subdomain=subdomain)
def showComparePlayersInfo():
    # player_json = PlayerDetailedRates(playerid, True)
    # print(player_json)
    return render_template("compareplayers.html", player_json = None, playerid=None)


@app.route("/compareplayers/<int:playerid>", subdomain=subdomain)
def showComparePlayerInfo(playerid):
    player_json = PlayerDetailedRates(playerid, True)
    # print(player_json)
    return render_template("drawplayer.html", player_json = player_json, playerid=playerid)



@app.route("/oneteamplay", subdomain=subdomain)
def showOneTeamPlayInfo():
    # player_json = PlayerDetailedRates(playerid, True)
    # print(player_json)
    return render_template("oneteamplay.html")


@app.route("/tournament/<int:tournamentid>", subdomain=subdomain)
def showTournamentInfo(tournamentid):
    ts = time.time()
    conn = get_db_connection()
    print("conn", time.time()-ts)

    tournament_info = conn.execute('SELECT * FROM data.tournaments as tournaments LEFT JOIN tournamentshardnes ON tournaments.tournamentid == tournamentshardnes.tournamentid WHERE tournaments.tournamentid = '+str(tournamentid)).fetchone() 

    tournaments = conn.execute('SELECT * FROM data.results as results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' +  
    ' WHERE results.tournamentid = '+str(tournamentid) + #+
    ' ORDER BY totalquestions DESC, teamrating DESC;'
    ).fetchall()
    # print(tuple(tournaments[0]))
    # print(tournaments[0].keys())
    # print(tournaments[0]['teamid'])
    conn.close()
    print("All time", time.time()-ts)
    if tournament_info: 
        return render_template("tournament.html", tourresults=tournaments, tournamentid = tournamentid, tournament_info = tournament_info)
    else:
        return "Данных о турнире "+str(tournamentid)+" не найдено"


@app.route("/tournament_full/<int:tournamentid>", subdomain=subdomain)
@app.route("/tournament/<int:tournamentid>/tours", subdomain=subdomain)
def showFullTournamentFullInfo(tournamentid):
    conn = get_db_connection()
    tournaments = conn.execute('SELECT * FROM data.results as results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' +  
    ' WHERE results.tournamentid = '+str(tournamentid) + ";"#+
    # ' ORDER BY place'
    ).fetchall()
    
    # tournament_info = conn.execute('SELECT * FROM data.tournaments as tournaments  WHERE tournamentid = '+str(tournamentid)).fetchone() 
    tournament_info = conn.execute('SELECT * FROM data.tournaments as tournaments LEFT JOIN tournamentshardnes ON tournaments.tournamentid == tournamentshardnes.tournamentid WHERE tournaments.tournamentid = '+str(tournamentid)).fetchone() 

    tours_number_info = conn.execute('SELECT max(leg) FROM tournaments_legs WHERE tournaments_legs.tournamentid = ' +str(tournamentid)).fetchall()
    tours_number = 0
    if len(tours_number_info) >0:
        if not tours_number_info[0][0] is None:
            tours_number = tours_number_info[0][0]

    leg_info = conn.execute('SELECT teamid, leg, legquestions, predictedquestions FROM tournaments_legs WHERE tournaments_legs.tournamentid = ' +str(tournamentid)).fetchall()
    leg_dict = {}
    for l in leg_info:
        if not l["teamid"] in leg_dict:
            leg_dict[l["teamid"]] = {}
        leg_dict[l["teamid"]][l["leg"]] = {"predict":l["predictedquestions"], "get":l["legquestions"]}
    
    conn.close()
    return render_template("tournament_full.html", tourresults=tournaments, tournamentid = tournamentid, tournament_info = tournament_info, tours_number=tours_number, leg_dict = leg_dict)


@app.route("/legs_info/<int:tournamentid>/<int:teamid>", subdomain=subdomain)
def showLegInfo(tournamentid, teamid):
    print("start showLeg")
    field = request.args.get('field', default = "questions", type = str)
    if field in ["legsize", "mask", "legquestions", "predictedquestions", "atleastprob", "atmostprob"]:
        conn = get_db_connection()
        leg_info = conn.execute('SELECT '+field+' FROM tournaments_legs '+
                               'WHERE tournaments_legs.tournamentid = ' +str(tournamentid) + " AND tournaments_legs.teamid = " +str(teamid)+
                               ' ORDER BY leg').fetchall()
        conn.close()
        if field in ["atleastprob", "atmostprob"]:
            text = ' '.join([str(round(t[field]*100, 2))+"%" for t in leg_info])
        else:
            text = ' '.join([str(round(t[field], 2)) for t in leg_info])
    else:
        print("end showLeg")
        return("")
    print("end showLeg")
    return(text)


@app.route("/teams/<int:teamid>/<int:tournamentid>", subdomain=subdomain)
def showTeamTournamentInfo(teamid, tournamentid, return_html = True):
    ts = time.time()
    conn = get_db_connection()
    if tournamentid == 0:
        relise_info = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratingsdelta').fetchone()
        release_id = relise_info["releaseid"]
    else:
        relise_info = conn.execute('SELECT * FROM playerratingsdelta '+
                                'WHERE playerratingsdelta.tournamentid = ' +str(tournamentid)).fetchone()
        if not relise_info is None:
            release_id = relise_info["releaseid"] - 1
        else: 
            release_id = 159 #temporel nevermore fix
   
    if tournamentid == 0:
        roster = conn.execute('SELECT * FROM data.base_roster as base_roster '+
        'JOIN playerratings ON base_roster.player_id=playerratings.playerid' +
        ' AND base_roster.teamid = ' + str(teamid) +
        ' AND playerratings.releaseid = ' + str(release_id) + 
        ' AND base_roster.releaseid = ' + str(release_id) + 
        " JOIN data.players as players ON base_roster.player_id=players.playerid" +
        ' ORDER BY playerratings.playerrating DESC'
        ).fetchall()
    else:   
        roster = conn.execute('SELECT * FROM roster '+
        'JOIN playerratings ON roster.playerid=playerratings.playerid' +
        ' AND roster.teamid = ' + str(teamid) +
        ' AND roster.tournamentid = ' + str(tournamentid) +
        ' AND playerratings.releaseid = ' + str(release_id) + 
        " JOIN data.players as players ON roster.playerid=players.playerid" +
        ' ORDER BY playerratings.playerrating DESC'
        ).fetchall()
  
  
    conn.close()
    ts2 = time.time()
    # text = '<br>'.join([str(round(t["playerrating"]))+" "+t["fullname"] for t in roster])
    if return_html:
        text = '<br>'.join([str(round(t["playerrating"]))+' <a href="/player/'+str(t["playerid"])+'"> '+t["fullname"] +"</a>" for t in roster])
        # print("times",ts2-ts3, ts3-ts1, ts2-ts, ts1 - ts)
        return text
    else:
        return ([dict(x) for x in roster])
    # return render_template("roster.html", roster=roster)


@app.route("/friendship/<int:tournamentid>", subdomain=subdomain)
def showPregeneratedFriendship(tournamentid):
    if os.path.isfile(f"Site/templates/{subdomain}/friendship/{tournamentid}.html"): 
        return render_template(f"{subdomain}/friendship/{tournamentid}.html")
    else:
        return "Прогноза для турнира "+str(tournamentid)+" не найдено"
    # return render_template("predict.html",)


@app.route("/predict/<int:tournamentid>", subdomain=subdomain)
def showPregeneratedPrediction(tournamentid):
    if os.path.isfile(f"Site/templates/predictions/{tournamentid}.html"): 
        return render_template(f"predictions/{tournamentid}.html")
    else:
        return "Прогноза для турнира "+str(tournamentid)+" не найдено"
    # return render_template("predict.html",)




@app.route("/predict/<int:tournamentid>/<int:questionstournamentid>", subdomain=subdomain)
def showPrediction(tournamentid, questionstournamentid):
    
    conn = get_db_connection()
    # print("conn", time.time()-ts)

    tournament_info = conn.execute('SELECT * FROM data.tournaments as tournaments  WHERE tournamentid = '+str(tournamentid)).fetchone() 
    qtournament_info = conn.execute('SELECT * FROM data.tournaments as tournaments  WHERE tournamentid = '+str(questionstournamentid)).fetchone() 

    tournaments = conn.execute('SELECT * FROM data.results as results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' +  
    ' WHERE results.tournamentid = '+str(tournamentid) + #+
    ' ORDER BY teamrating DESC;'
    ).fetchall()

    qv_info = conn.execute('SELECT * FROM questionrating ' +  
    ' WHERE tournamentid = '+str(questionstournamentid) +";"
    ).fetchall()
    qv = [r["hardnes"] for r in qv_info]

    
    trn = []
    pls = 0
    for t in tournaments:
        trn.append(dict(t))
        trn[-1]["predictedquestions"] = rt.ELO_estimate(trn[-1]["teamrating"], qv)
        pls += 1
        trn[-1]["place"] = pls

    # print(tuple(tournaments[0]))
    # print(tournaments[0].keys())
    # print(tournaments[0]['teamid'])
    conn.close()
    # print("All time", time.time()-ts)
    if tournament_info: 
        return render_template("predict.html", tourresults=trn, tournamentid = tournamentid, tournament_info = tournament_info, qtournament_info = qtournament_info)
    else:
        return "Данных о турнире "+str(tournamentid)+" не найдено"
    # return render_template("predict.html",)

@app.route("/funstat/rozhkov", subdomain=subdomain)
def showRozhkov():
    return render_template("funstat/rozhkov.html")

@app.route("/funstat/by_author/<int:authorid>", subdomain=subdomain)
def showPregeneratedAuthorStats(authorid):
    if os.path.isfile(f"Site/templates/funstat/by_author/{authorid}.html"): 
        return render_template(f"funstat/by_author/{authorid}.html")
    else:
        return "Статистики по автору "+str(authorid)+" нет"
    # return render_template("predict.html",)

@app.route("/funstat/by_series/<int:authorid>", subdomain=subdomain)
def showPregeneratedSeriesStats(authorid):
    if os.path.isfile(f"Site/templates/funstat/by_series/{authorid}.html"): 
        return render_template(f"funstat/by_author/{authorid}.html")
    else:
        return "Статистики по серии с id "+str(authorid)+" нет"
    # return render_template("predict.html",)

@app.route("/predict/studchr2024", subdomain=subdomain)
def showStudChR():
    return render_template("studchr24.html")

@app.route("/fantasy/schr", subdomain=subdomain)
def showStudChRFant():
    return render_template("studchr24fantasy.html")

@app.route("/predict/nevermore2024", subdomain=subdomain)
@app.route("/nevermore2024", subdomain=subdomain)
def showNevermore2024():
    return render_template("nevermore24.html")


@app.route("/predict/nevermore2025", subdomain=subdomain)
@app.route("/nevermore2025", subdomain=subdomain)
@app.route("/nevermore", subdomain=subdomain)
def showNevermore2025():
    return render_template("predictions/10011859.html")


@app.route("/nevermore_v2", subdomain=subdomain)
def showNevermore2():
    return render_template("nevermore2405.html")

@app.route("/predict/gostinydvor", subdomain=subdomain)
@app.route("/predict/10707", subdomain=subdomain)
def showGD():
    return render_template("10707.html")

@app.route("/predict/nesova2024", subdomain=subdomain)
@app.route("/nesova2024", subdomain=subdomain)
@app.route("/compare", subdomain=subdomain)
def showCompare():
    return render_template("compare.html")



@app.route("/api/teams/<int:teamid>/full", subdomain=subdomain)
def gatherTeamInfo(teamid, return_json = True):
    team_data = {}
    conn = get_db_connection()
    team_name = conn.execute(f'SELECT teamname FROM data.teams as teams WHERE teamid = {teamid}').fetchone()
    if team_name is None:
        team_data["team_name"] = ""
    else:
        team_data["team_name"] = team_name["teamname"]

    tournaments = conn.execute('SELECT * FROM data.results as results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' + 
    ' JOIN  data.tournaments as tournaments  ON results.tournamentid=tournaments.tournamentid' + 
    ' WHERE results.teamid = '+str(teamid) + 
    ' ORDER BY tournaments.dateEnd DESC'
    )#.fetchall()
    team_data["tournaments"] = [dict(x) for x in tournaments]
    if return_json:
        return json.dumps(team_data)
    else:
        return team_data


@app.route("/teams/<int:teamid>", subdomain=subdomain)
def showTeamInfo(teamid):
    conn = get_db_connection()
    team_name = conn.execute(f'SELECT teamname FROM data.teams as teams WHERE teamid = {teamid}').fetchone()
    if team_name is None:
        team_name = ""
    else:
        team_name = team_name["teamname"]
    tournaments = conn.execute('SELECT * FROM data.results as results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' + 
    ' JOIN  data.tournaments as tournaments  ON results.tournamentid=tournaments.tournamentid' + 
    ' WHERE results.teamid = '+str(teamid) + 
    ' ORDER BY tournaments.dateEnd DESC'
    ).fetchall()
    # print(tuple(tournaments[0]))
    # print(tournaments[0].keys())
    # print(tournaments[0]['teamid'])
    team_base_roster = showTeamTournamentInfo(teamid, 0, False)
    if len(team_base_roster)>0:
        team_rating = rt.independed_ELO([x["playerrating"] for x in team_base_roster][:6])
    else:
        team_rating = 0
    releaseid = rt.season_by_datetime(datetime.datetime.now())
    place_req = conn.execute(f"SELECT teambaserating, place FROM teambaseratings WHERE teamid={teamid} and releaseid = {releaseid}").fetchall()

    if len(place_req) > 0:
        place_info = dict(place_req[0])
        place_info["page"] = ceil(place_info["place"]/100)
    else:
        place_info = None
    conn.close()
    return render_template("team.html", tourresults=tournaments, teamid = teamid, team_base_roster = team_base_roster, team_rating = team_rating, team_name = team_name, place_info=place_info)

@app.route("/tournaments", subdomain=subdomain)
def showAllTournaments():
    today = datetime.datetime.now()
    conn = get_db_connection()
    tournaments = conn.execute('SELECT * FROM data.tournaments as tournaments LEFT JOIN tournamentshardnes ON tournaments.tournamentid== tournamentshardnes.tournamentid WHERE dateEnd < \''+today.strftime("%Y-%m-%d %H:%M:%S")+'\' ORDER BY dateEnd DESC').fetchall()
    print(today.strftime("%Y-%m-%dT%H:%M:%S"))
    conn.close()
    return render_template("alltournaments.html", toursinfo=tournaments)
    

def read_cfg():
    website_url = ""
    port = 80
    try:
        with open("site.cfg") as cfg_file:
            website_url = cfg_file.readline().strip()
            port = int(cfg_file.readline().strip())
    except Exception:
        pass    
    if website_url == "":
        website_url = 'chgk.test'
        port = 80
    return website_url, port





app.run(debug=True, port=port)
    