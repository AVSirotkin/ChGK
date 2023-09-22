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
    ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC LIMIT 500 OFFSET '+str(500*(page-1))).fetchall()
    # ratings = conn.execute('SELECT players.playerid as playerid, players.fullname as fullname, pr.playerrating as playerrating, pr.releaseid as releaseid FROM (SELECT * FROM playerratings WHERE releaseid='+str(season)+' ORDER BY playerrating DESC LIMIT 500) as pr JOIN players ON pr.playerid=players.playerid ORDER BY pr.playerrating DESC LIMIT 500').fetchall()
    #players.playerid as playerid, players.fullname as fullname, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid
    t2= time.time()
    print(t2 - t1, len(ratings))
    conn.close()
    return render_template("allplayers.html", ratings=ratings)


@app.route("/player/<int:playerid>", subdomain="rating")
def showPlayerInfo(playerid):
    conn = get_db_connection()
    deltas = conn.execute('SELECT * FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE playerratingsdelta.playerid = '+str(playerid)+' ORDER BY playerratingsdelta.releaseid DESC').fetchall()
    ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
    conn.close()
    return render_template("player.html", ratings=ratings, deltas=deltas)

@app.route("/tournament/<int:tournamentid>", subdomain="rating")
def showTournamentInfo(tournamentid):
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
    return render_template("tournament.html", tourresults=tournaments, tournamentid = tournamentid)


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
    




@app.route("/teams/<int:teamid>/<int:tournamentid>", subdomain="rating")
def showTeamTournamentInfo(teamid, tournamentid):
    conn = get_db_connection()
    relise_info = conn.execute('SELECT * FROM playerratingsdelta '+
                               'WHERE playerratingsdelta.tournamentid = ' +str(tournamentid)).fetchone()
    release_id = relise_info["releaseid"] - 1
    
    # print(relise_info["releaseid"])

    roster = conn.execute('SELECT * FROM roster '+
    'JOIN playerratings ON roster.playerid=playerratings.playerid' + 
    " JOIN players ON roster.playerid=players.playerid"
    ' WHERE roster.teamid = ' + str(teamid) +
    ' AND roster.tournamentid = ' + str(tournamentid) + 
    ' AND playerratings.releaseid = ' + str(release_id) + 
    ' ORDER BY playerratings.playerrating DESC'
    ).fetchall()
    # print(tuple(tournaments[0]))
    # print(tournaments[0].keys())
    # print(tournaments[0]['teamid'])
    conn.close()
    text = '<br>'.join([str(round(t["playerrating"]))+" "+t["fullname"] for t in roster])
    return text
    # return render_template("roster.html", roster=roster)



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