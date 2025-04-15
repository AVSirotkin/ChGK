# %%
import requests
import json

personid = 335

with open("stats_by_author.json", "rt", encoding = "utf8") as f:
    config_info = json.load(f) 

personid = config_info["personid"]
file_name = config_info["file_name"]
authora = config_info["authorA"]


# %%
all_Rozhkov = []
request_link = f"https://gotquestions.online/api/persons/{personid}/questions/"
while not request_link is None:
    res = requests.get(request_link).json()
    request_link = res['next']
    all_Rozhkov += res['results']

# %%
# len(all_Rozhkov)
Rozhkov_by_tour = {}
for x in all_Rozhkov:
    if x["ts_id"] not in Rozhkov_by_tour:
        Rozhkov_by_tour[x["ts_id"]] = []
    if x["number"]>0:
        Rozhkov_by_tour[x["ts_id"]].append(x["number"]-1)            

# %%
tours = set({x["ts_id"] for x in all_Rozhkov})

# %%
def prob(r,q):
    return(1/(1+10**((q-r)/400)))


# %%
import sqlite3

players_stat = {}

conn = sqlite3.connect("../Output/rating.db")

# %%
players_stat = {}

for tourid in Rozhkov_by_tour:
    local_team_results = {}
    result = conn.execute(f"SELECT results.teamid, teamrating, mask FROM results INNER JOIN tournamentratings ON results.tournamentid == tournamentratings.tournamentid AND results.teamid == tournamentratings.teamid WHERE results.tournamentid == {tourid}").fetchall()
    if len(result) == 0:
        continue
    result = conn.execute(f"SELECT results.teamid, teamrating, mask FROM results INNER JOIN tournamentratings ON results.tournamentid == tournamentratings.tournamentid AND results.teamid == tournamentratings.teamid WHERE results.tournamentid == {tourid}").fetchall()
    played = len([i for i in Rozhkov_by_tour[tourid] if i < len(result[0][2])])
    if played == 0:
        continue

    roster = conn.execute(f"SELECT teamid, playerid FROM roster WHERE tournamentid=={tourid}").fetchall()
    hardnes = conn.execute(f"SELECT hardnes, questionid FROM questionrating WHERE tournamentid=={tourid}").fetchall()
    played = len([i for i in Rozhkov_by_tour[tourid] if i < len(result[0][2])])
    q_ids = [i for i in Rozhkov_by_tour[tourid] if i < len(result[0][2])]
    for t in result:
        if t[2] is None:
            continue
        local_team_results[t[0]] = {"teamid":t[0], "tournamentid":tourid, "played": played, "get":sum(t[2][i]=="1" for i in q_ids), "predict":sum(prob(t[1], h[0]) for h in hardnes if (h[1]-1) in q_ids)}
    
    for p in roster:
        if not p[0] in local_team_results:
            continue
        if not p[1] in players_stat:
            plinfo = conn.execute(f"SELECT surname, name from players WHERE playerid == {p[1]}").fetchone()
            players_stat[p[1]] = {"name":plinfo[0]+" "+plinfo[1],"total_get": 0, "total_played":0, "predicted":0, "detailed":[]}
        players_stat[p[1]]["detailed"].append(local_team_results[p[0]])
        players_stat[p[1]]["total_played"] += local_team_results[p[0]]["played"]
        players_stat[p[1]]["total_get"] += local_team_results[p[0]]["get"]
        players_stat[p[1]]["predicted"] += local_team_results[p[0]]["predict"]

# %%

table_head = '''
    <thead>
	<tr><th>Игрок</th><th>Сыграно</th><th>Взято</th><th>Прогноз</th><th>Взято-Прогноз</th><th>Взято/Сыграно</th><th>(Взято-Прогноз)/Сыграно</th><th>(Взято-Прогноз)/Прогноз</th></tr>
   </thead>
    <tbody>
    '''
for plid in players_stat:
    table_head += f'<tr><td><a href = "/player/{plid}">{players_stat[plid]["name"]}</a></td><td>{players_stat[plid]["total_played"]}</td><td>{players_stat[plid]["total_get"]}</td><td>{players_stat[plid]["predicted"]:0.2f}</td>'
    table_head += f"<td>{players_stat[plid]["total_get"] - players_stat[plid]["predicted"] :0.2f}</td><td>{players_stat[plid]["total_get"]/players_stat[plid]["total_played"]:0.2f}</td>"
    table_head += f"<td>{(players_stat[plid]["total_get"] - players_stat[plid]["predicted"])/players_stat[plid]["total_played"] :0.2f}</td><td>{(players_stat[plid]["total_get"] - players_stat[plid]["predicted"])/players_stat[plid]["predicted"]:0.2f}</td></tr>\n"

table_head += "</tbody>"
# print(table_head)

# %%
ft = open("..//Site//templates//funstat//by_author//by_author.html", "tr", encoding='utf-8').read()
ft = ft.replace("{{author_name}}", authora)
ft = ft.replace("{{table_to_insert}}", table_head)
fw = open("..//Site//templates//funstat//by_author//"+file_name, "tw", encoding='utf-8')
fw.write(ft)
fw.close()

# %%



