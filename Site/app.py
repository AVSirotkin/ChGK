import sqlite3
from flask import Flask, render_template
import datetime

app = Flask(__name__)


def get_db_connection():
    conn = sqlite3.connect('Output/rating.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return "Hello World"


@app.route('/about')
def about():
    return "About page"

@app.route('/players')
@app.route("/players/<int:season>")
def showAllPlayers(season = 0):
    conn = get_db_connection()
    if season == 0:
        tmp = conn.execute('SELECT * FROM playerratings ORDER BY releaseid DESC').fetchall()
        season = int(tmp[0]["releaseid"])
    ratings = conn.execute('SELECT players.playerid as playerid, players.full_name as full_name, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid FROM playerratings JOIN players ON playerratings.playerid=players.playerid WHERE releaseid='+str(season)+' ORDER BY playerratings.playerrating DESC').fetchall()
    #players.playerid as playerid, players.full_name as full_name, playerratings.playerrating as playerrating, playerratings.releaseid as releaseid
    conn.close()
    return render_template("allplayers.html", ratings=ratings)


@app.route("/player/<int:playerid>")
def showPlayerInfo(playerid):
    conn = get_db_connection()
    deltas = conn.execute('SELECT * FROM playerratingsdelta WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
    ratings = conn.execute('SELECT * FROM playerratings WHERE playerid = '+str(playerid)+' ORDER BY releaseid DESC').fetchall()
    conn.close()
    return render_template("player.html", ratings=ratings, deltas=deltas)

@app.route("/tournament/<int:tournamentid>")
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
    return render_template("tournament.html", tourresults=tournaments)
    


@app.route("/tournaments")
def showAllTournaments():
    today = datetime.datetime.now()
    conn = get_db_connection()
    tournaments = conn.execute('SELECT * FROM tournaments WHERE enddate < \''+today.strftime("%Y-%m-%d %H:%M:%S")+'\' ORDER BY enddate DESC').fetchall()
    print(today.strftime("%Y-%m-%dT%H:%M:%S"))
    conn.close()
    return render_template("alltournaments.html", toursinfo=tournaments)
    


if __name__ == "__main__":
    app.run(debug=True)