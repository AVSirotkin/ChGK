import sqlite3
from flask import Flask, render_template, request
import datetime
import time
import sys
sys.path.append('../API/')
sys.path.append('../Ratings')
sys.path.append('./Ratings')
import rating as rt
import json
import os.path

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('Output/rating_for_site.db')
    conn.row_factory = sqlite3.Row
    return conn


# @app.route('/', subdomain="rating")
# def ratingindex():
#     return "secret rating page"



@app.route('/')
def index():
    return "Hello World"

@app.route('/about')
def about():
    return "About page"

@app.route('/players', subdomain="rating")
@app.route("/players/<int:season>", subdomain="rating")
def showAllPlayers(season = 0):
    page = request.args.get('page', 1, type=int)
    ts = time.time()
    conn = get_db_connection()
    if season == 0:
        tmp = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratings').fetchall()
        season = int(tmp[0]["releaseid"])
    t1 = time.time()
    print(page, t1-ts)
    ratings = conn.execute('SELECT ROW_NUMBER() OVER(ORDER BY playerratings.playerrating DESC) AS position, players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, pr.playerrating as playerrating, pr.releaseid as releaseid FROM (SELECT * FROM playerratings WHERE releaseid='+str(season)+' ORDER BY playerrating DESC LIMIT 500) as pr JOIN players ON pr.playerid=players.playerid ORDER BY pr.playerrating DESC LIMIT 500').fetchall()
    #players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid
    # ratings["position"] = [x+1+(page-1)*500 for x in range(len(ratings))]
    t2= time.time()
    print(t2 - t1, len(ratings))
    conn.close()
    return render_template("allplayers.html", ratings=ratings, page = page)


@app.route('/api/questions/<int:tournamentid>', subdomain="rating")
def QuestionsHardnes(tournamentid):
    conn = get_db_connection()
    questions = conn.execute(f'SELECT hardnes FROM questionrating WHERE tournamentid == {tournamentid}').fetchall()
    return json.dumps([x['hardnes'] for x in questions])




@app.route('/', subdomain="rating")
@app.route('/teams', subdomain="rating")
def showAllTeams(season = 0):
    page = request.args.get('page', 1, type=int)
    ts = time.time()
    conn = get_db_connection()
    # if season == 0:
    #     tmp = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratings').fetchall()
        # season = int(tmp[0]["releaseid"])
    t1 = time.time()
    print(page, t1-ts)
    ratings = conn.execute('SELECT ROW_NUMBER() OVER(ORDER BY base_team_rates.team_rating  DESC) AS position, teams.teamid as teamid, teams.teamname as name, base_team_rates.team_rating as teamrating FROM base_team_rates JOIN teams ON base_team_rates.teamid=teams.teamid ORDER BY base_team_rates.team_rating DESC LIMIT 100 OFFSET '+str(100*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, pr.playerrating as playerrating, pr.releaseid as releaseid FROM (SELECT * FROM playerratings WHERE releaseid='+str(season)+' ORDER BY playerrating DESC LIMIT 500) as pr JOIN players ON pr.playerid=players.playerid ORDER BY pr.playerrating DESC LIMIT 500').fetchall()
    #players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid
    # ratings["position"] = [x+1+(page-1)*500 for x in range(len(ratings))]
    t2= time.time()
    print(t2 - t1, len(ratings))
    conn.close()
    return render_template("allteams.html", ratings=ratings, page = page)





@app.route("/player/<int:playerid>", subdomain="rating")
def showPlayerInfo(playerid):
    conn = get_db_connection()
    ts = time.time()
    # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    deltas = conn.execute('SELECT playerratingsdelta.tournamentid as tournamentid, releaseid, deltarating, teamname, name, playerratingsdelta.teamid as teamid FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.playerid = '+str(playerid) +' AND playerratingsdelta.tournamentid=tournaments.tournamentid JOIN results ON playerratingsdelta.tournamentid=results.tournamentid AND playerratingsdelta.teamid=results.teamid').fetchall()# ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # print([x["releaseid"] for x in deltas]  )
    deltas.sort(key=lambda x: -x["releaseid"])
    
    ts1 = time.time()
    # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid JOIN roster ON tournaments.tournamentid=roster.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
    # ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)).fetchall()
    ts2 = time.time()
    playername_req = conn.execute('SELECT fullname from players WHERE playerid='+str(playerid)).fetchone()
    if playername_req is None:
        playername = "Нет данных"
    else:
        playername = playername_req["fullname"]
    conn.close()
    print("deltas", ts1 - ts, "ratings", ts2-ts1)
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


    return render_template("player.html", ratings=rate_list, playerid=playerid, playername=playername)

@app.route("/tournament/<int:tournamentid>", subdomain="rating")
def showTournamentInfo(tournamentid):
    ts = time.time()
    conn = get_db_connection()
    print("conn", time.time()-ts)

    tournament_info = conn.execute('SELECT * FROM tournaments WHERE tournamentid = '+str(tournamentid)).fetchone() 

    tournaments = conn.execute('SELECT * FROM results '+
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


@app.route("/tournament_full/<int:tournamentid>", subdomain="rating")
def showFullTournamentInfo(tournamentid):
    conn = get_db_connection()
    tournaments = conn.execute('SELECT * FROM results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' +  
    ' WHERE results.tournamentid = '+str(tournamentid) + ";"#+
    # ' ORDER BY place'
    ).fetchall()
    # print(tuple(tournaments[0]))
    print(tournaments[0].keys())
    print(tournaments[0]['teamid'])
    conn.close()
    return render_template("tournament_full.html", tourresults=tournaments)


@app.route("/legs_info/<int:tournamentid>/<int:teamid>", subdomain="rating")
def showLegInfo(tournamentid, teamid):
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
        return("")
    return(text)


@app.route("/teams/<int:teamid>/<int:tournamentid>", subdomain="rating")
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
        roster = conn.execute('SELECT * FROM base_roster '+
        'JOIN playerratings ON base_roster.player_id=playerratings.playerid' +
        ' AND base_roster.teamid = ' + str(teamid) +
        ' AND playerratings.releaseid = ' + str(release_id) + 
        " JOIN players ON base_roster.player_id=players.playerid" +
        ' ORDER BY playerratings.playerrating DESC'
        ).fetchall()
    else:   
        roster = conn.execute('SELECT * FROM roster '+
        'JOIN playerratings ON roster.playerid=playerratings.playerid' +
        ' AND roster.teamid = ' + str(teamid) +
        ' AND roster.tournamentid = ' + str(tournamentid) +
        ' AND playerratings.releaseid = ' + str(release_id) + 
        " JOIN players ON roster.playerid=players.playerid" +
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


@app.route("/predict/<int:tournamentid>", subdomain="rating")
def showPregeneratedPrediction(tournamentid):
    if os.path.isfile(f"Site/templates/predictions/{tournamentid}.html"): 
        return render_template(f"predictions/{tournamentid}.html")
    else:
        return "Прогноза для турнира "+str(tournamentid)+" не найдено"
    # return render_template("predict.html",)



@app.route("/predict/<int:tournamentid>/<int:questionstournamentid>", subdomain="rating")
def showPrediction(tournamentid, questionstournamentid):
    
    conn = get_db_connection()
    # print("conn", time.time()-ts)

    tournament_info = conn.execute('SELECT * FROM tournaments WHERE tournamentid = '+str(tournamentid)).fetchone() 
    qtournament_info = conn.execute('SELECT * FROM tournaments WHERE tournamentid = '+str(questionstournamentid)).fetchone() 

    tournaments = conn.execute('SELECT * FROM results '+
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



@app.route("/predict/studchr2024", subdomain="rating")
def showStudChR():
    return render_template("studchr24.html")

@app.route("/fantasy/schr", subdomain="rating")
def showStudChRFant():
    return render_template("studchr24fantasy.html")

@app.route("/predict/nevermore2024", subdomain="rating")
@app.route("/nevermore2024", subdomain="rating")
@app.route("/nevermore", subdomain="rating")
def showNevermore():
    return render_template("nevermore24.html")


@app.route("/nevermore_v2", subdomain="rating")
def showNevermore2():
    return render_template("nevermore2405.html")

@app.route("/predict/gostinydvor", subdomain="rating")
@app.route("/predict/10707", subdomain="rating")
def showGD():
    return render_template("10707.html")

@app.route("/predict/nesova2024", subdomain="rating")
@app.route("/nesova2024", subdomain="rating")
@app.route("/compare", subdomain="rating")
def showCompare():
    return render_template("compare.html")

@app.route("/teams/<int:teamid>", subdomain="rating")
def showTeamInfo(teamid):
    conn = get_db_connection()
    team_name = conn.execute(f'SELECT teamname FROM teams WHERE teamid = {teamid}').fetchone()
    if team_name is None:
        team_name = ""
    else:
        team_name = team_name["teamname"]
    tournaments = conn.execute('SELECT * FROM results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' + 
    ' JOIN tournaments ON results.tournamentid=tournaments.tournamentid' + 
    ' WHERE results.teamid = '+str(teamid) + 
    ' ORDER BY tournaments.enddate DESC'
    ).fetchall()
    # print(tuple(tournaments[0]))
    # print(tournaments[0].keys())
    # print(tournaments[0]['teamid'])
    conn.close()
    team_base_roster = showTeamTournamentInfo(teamid, 0, False)
    if len(team_base_roster)>0:
        team_rating = rt.independed_ELO([x["playerrating"] for x in team_base_roster][:6])
    else:
        team_rating = 0
    return render_template("team.html", tourresults=tournaments, teamid = teamid, team_base_roster = team_base_roster, team_rating = team_rating, team_name = team_name)

@app.route("/tournaments", subdomain="rating")
def showAllTournaments():
    today = datetime.datetime.now()
    conn = get_db_connection()
    tournaments = conn.execute('SELECT * FROM tournaments WHERE enddate < \''+today.strftime("%Y-%m-%d %H:%M:%S")+'\' ORDER BY enddate DESC').fetchall()
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

if __name__ == "__main__":
    website_url, port = read_cfg()
    print(website_url)
    app.config['SERVER_NAME'] = website_url
    app.run(debug=True, port=port)
    