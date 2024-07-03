import sqlite3
from flask import Flask, render_template, request
import datetime
import time

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('Output/rating.db')
    conn.row_factory = sqlite3.Row
    return conn


@app.route('/', subdomain="rating")
def ratingindex():
    return "secret rating page"



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
    deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    # deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid JOIN roster ON tournaments.tournamentid=roster.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
    playername = conn.execute('SELECT fullname from players WHERE playerid='+str(playerid)).fetchone()["fullname"]
    conn.close()
    return render_template("player.html", ratings=ratings, deltas=deltas, playerid=playerid, playername=playername)

@app.route("/tournament/<int:tournamentid>", subdomain="rating")
def showTournamentInfo(tournamentid):
    ts = time.time()
    conn = get_db_connection()
    print("conn", time.time()-ts)

    tournament_info = conn.execute('SELECT * FROM tournaments WHERE tournamentid = '+str(tournamentid)).fetchone() 

    tournaments = conn.execute('SELECT * FROM results '+
    'JOIN tournamentratings ON results.teamid=tournamentratings.teamid AND results.tournamentid=tournamentratings.tournamentid' +  
    ' WHERE results.tournamentid = '+str(tournamentid) + ";"#+
    # ' ORDER BY place'
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
def showTeamTournamentInfo(teamid, tournamentid):
    ts = time.time()
    conn = get_db_connection()
    if tournamentid == 0:
        relise_info = conn.execute('SELECT MAX(releaseid) as releaseid FROM playerratingsdelta').fetchone()
        release_id = relise_info["releaseid"]
    else:
        relise_info = conn.execute('SELECT * FROM playerratingsdelta '+
                                'WHERE playerratingsdelta.tournamentid = ' +str(tournamentid)).fetchone()
        release_id = relise_info["releaseid"] - 1
   
    # # print([dict(x) for x in conn.execute('EXPLAIN QUERY PLAN SELECT * FROM roster '+
    # # 'JOIN playerratings ON roster.playerid=playerratings.playerid' + 
    # # " JOIN players ON roster.playerid=players.playerid"
    # # ' WHERE roster.teamid = ' + str(teamid) +
    # # ' AND roster.tournamentid = ' + str(tournamentid) + 
    # # ' AND playerratings.releaseid = ' + str(release_id) #+ 
    # # # ' ORDER BY playerratings.playerrating DESC'
    # # ).fetchall()])
   
    
    # ts1 = time.time()
    
  
    # roster = conn.execute('SELECT * FROM roster '+
    # 'JOIN playerratings ON roster.playerid=playerratings.playerid' + 
    # #" JOIN players ON roster.playerid=players.playerid"
    # ' WHERE roster.teamid = ' + str(teamid) +
    # ' AND roster.tournamentid = ' + str(tournamentid) + 
    # ' AND playerratings.releaseid = ' + str(release_id) + 
    # ' ORDER BY playerratings.playerrating DESC'
    # ).fetchall()
    # # print(tuple(tournaments[0]))
    # # print(tournaments[0].keys())
    # # print(tournaments[0]['teamid'])
  
    # ts3 = time.time()
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
    text = '<br>'.join([str(round(t["playerrating"]))+' <a href="/player/'+str(t["playerid"])+'"> '+t["fullname"] +"</a>" for t in roster])
    # print("times",ts2-ts3, ts3-ts1, ts2-ts, ts1 - ts)
    return text
    # return render_template("roster.html", roster=roster)



@app.route("/predict/studchr2024", subdomain="rating")
def showStudChR():
    return render_template("studchr24.html")

@app.route("/fantasy/schr", subdomain="rating")
def showStudChRFant():
    return render_template("studchr24fantasy.html")



@app.route("/predict/nesova2024", subdomain="rating")
@app.route("/nesova2024", subdomain="rating")
@app.route("/compare", subdomain="rating")
def showCompare():
    return render_template("compare.html")

@app.route("/teams/<int:teamid>", subdomain="rating")
def showTeamInfo(teamid):
    conn = get_db_connection()
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
    return render_template("team.html", tourresults=tournaments, teamid = teamid)

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
    try:
        with open("site.cfg") as cfg_file:
            website_url = cfg_file.readline().strip()
    except Exception:
        pass    
    if website_url == "":
        website_url = 'chgk.fun'
    return website_url

if __name__ == "__main__":
    website_url = read_cfg()
    print(website_url)
    app.config['SERVER_NAME'] = website_url
    app.run(debug=True, port=80)