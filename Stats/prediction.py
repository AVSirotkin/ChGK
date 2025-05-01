# %%
import sqlite3
import json

# %%
conn = sqlite3.connect(r'Output/rating.db')


# %%
import sys
sys.path.append('API/')
sys.path.append('Ratings')
from site_api_tools import ChGK_API_connector
import rating as rt
connector = ChGK_API_connector()

if len(sys.argv) <= 1:
    print("Use command 'python prediction.py param.json'")
    param_fname = "Stats/param.json"
else:
    param_fname = sys.argv[1]

with open(param_fname, "rt", encoding='utf-8') as param_f:
    param_dict = json.load(param_f)

# tounament_name = 'V Гран-при текстильной столицы'
# Venue_names = ["Иваново"]
# Venue_tour_id = [10906]

tounament_name = param_dict["tounament_name"]
Venue_names    = param_dict["venue_names"]
Venue_tour_id  = param_dict["venue_tour_id"]
release        = param_dict["release"]
tour_names     = param_dict["tour_names"]
tour_ids       = param_dict["tour_ids"]
# tour_multiplier= param_dict["tour_multiplier"]


all_teams = []
venue_by_id = {}
for n,p in zip(Venue_names, Venue_tour_id):
    # teams = connector.tournament_results(p, forced=True)
    teams = connector.tournament_results(p, forced=True)
    for t in teams:
        t["venue"] = n
        all_teams.append(t)
        venue_by_id[t["team"]["id"]] = n

# %%
teams = all_teams#teams_never#teams_neh + teams_sec
# teams = connector.tournament_results(10677)

# %%
team_rosters_text = {}

# %%
# release = 187
rates = {}
pl_rates = {}

team_rates = {}
team_names = {}
name_ids = {}
for t in teams:
    tid = t["team"]["id"]
    print(t)
    print(tid)
    team_names[tid] = t["current"]["name"]
    name_ids[t["current"]["name"]] = tid
    rates[tid] = []
    roster = []
    for pl in t["teamMembers"]:
        print(pl)
        sql_req = f"SELECT * FROM playerratings WHERE playerid = {pl['player']['id']} and releaseid = {release}"
        row = conn.execute(sql_req).fetchone()
        print(row)
        if row is None:
            rates[tid].append(900)
        else:
            rates[tid].append(row[2])
            pl_rates[pl['player']["surname"]+" "+pl['player']["name"]] = row[2]
        roster.append({"playerid":pl['player']['id'], "playerrating":int(rates[tid][-1]), "fullname": pl['player']["surname"]+" "+pl['player']["name"] + ("" if (pl['player']["patronymic"] is None) else (" "+pl['player']["patronymic"]))}) 
    if len(rates[tid]) > 0:
        team_rates[tid] = rt.independed_ELO(sorted(rates[tid])[-6:],rt.INDEPNDENT_SKILL_QUESTION)
    else:
        team_rates[tid] = 0
    
    text = '<br>'.join([str(round(t["playerrating"]))+' <a href="/player/'+str(t["playerid"])+'"> '+t["fullname"] +"</a>" for t in sorted(roster, key=lambda x: -x["playerrating"])])
    team_rosters_text[tid] = text


# %%
team_roster_text_script =  "<script>\n var team_rosters_text ="+ json.dumps(team_rosters_text)+"\n</script>"

# %%
# for tid in team_names:
team_names_text = str([team_names[tid] for tid in team_names])

# %%
ft = open("Site//templates//predict_full.html", "tr", encoding='utf-8').read()
ft = ft.replace("{{team_names_text}}", team_names_text)
ft = ft.replace("{{team_roster_text_script}}",team_roster_text_script)
ft = ft.replace("{{tounament_name}}", tounament_name)

# %%
sorted_tid = [x for x in team_names]


sorted_tid.sort(key= lambda x: -team_rates[x])

# %%
# tour_names = ["Чемпионат Германии 2023 (TrueDL 5.2)", "Кубок княгини Ольги-2024 (TrueDL 4.9)", "Студенческий чемпионат России 2024 (TrueDL 5.7)", "Сугробушки (TrueDL 4,9)"]
# tour_ids = [9677, 10892, 10677, 9933]
# tour_names = ["IV Гран-при текстильной столицы (TrueDL 6.0)", "Вышкафест — 2025  (TrueDL 6.1)", "Весна в ЛЭТИ (TrueDL 5.7)"]
# tour_ids = [9532, 11808, 11740]


qrates = []

tour_options_str = ""
for nm in tour_names:
    tour_options_str += f'<option>Как на {nm}</option>'
    # <option>Как на Nevermore-2 2022 (TrueDL 6.7)</option>

for id in tour_ids:
    qrates.append([row[2] for row in conn.execute(f"SELECT * FROM questionrating WHERE tournamentid = {id}")])

ft = ft.replace("{{question_hardnes_names}}", tour_options_str)

# %%
to_get = []
all_exact = []
for i in range(len(tour_ids)):
    to_get.append({})
    all_exact.append({})
    for tid in team_rates:
        to_get[-1][tid] = rt.ELO_estimate(team_rates[tid], qrates[i])
        all_exact[-1][tid] = rt.estimate_exact_prob(team_rates[tid], qrates[i])

# %%
all_data = []
for idx in range(len(tour_ids)):
  all_data.append([])
  x=[i for i in range(len(qrates[idx])+1)]
  for tid in team_names:
      all_data[-1].append({
    "x": x,
    "y": [round(x, 6) for x in all_exact[idx][tid]],
    "name":  team_names[tid],
    "type": 'bar'
  })

# all_data2 = []
# x=[i for i in range(len(qrate_nev_2022)+1)]
# for tid in team_names:
#     all_data2.append({
#   "x": x,
#   "y": [round(x, 6) for x in all_exact_nev_2022[tid]],
#   "name":  team_names[tid],
#   "type": 'bar'
# })    

# all_data3 = []
# x=[i for i in range(len(qrate_schr_2023)+1)]
# for tid in team_names:
#     all_data3.append({
#   "x": x,
#   "y": [round(x, 6) for x in all_exact_schr_2023[tid]],
#   "name":  team_names[tid],
#   "type": 'bar'
# }) 
    
#     all_data4 = []
# x=[i for i in range(len(qrate_neh_2022)+1)]
# for tid in team_names:
#     all_data4.append({
#   "x": x,
#   "y": [round(x, 6) for x in all_exact_schr_2022[tid]],
#   "name":  team_names[tid],
#   "type": 'bar'
# }) 

# %%
ft = ft.replace("{{const_data_script}}" ,"<script>\n const data1 = " + json.dumps(all_data, ensure_ascii=False)+ " \n</script>")

# %%
loc_places = {}
table_body = ""
for v in Venue_names:
    loc_places[v] = 0

for tid in sorted_tid:
    table_body += f"<tr><td>{sum([loc_places[v] for v in loc_places]) + 1}</td>"
    if len(Venue_tour_id) > 1:
        table_body += f"<td>{loc_places[venue_by_id[tid]] + 1}</td><td>{venue_by_id[tid]}</td>"
    table_body += f"<td><a href='/teams/{tid}'>{team_names[tid]}</a><div id='roster{tid}'> <div onclick='my_show({tid})'>(состав)</div></td><td>{team_rates[tid]:.2f}</td>"
    
    for i in range(len(tour_ids)):
        table_body += f"<td>{to_get[i][tid]:.2f}</td>"
    table_body +="</tr>\n"
    loc_places[venue_by_id[tid]] += 1

# %%
table_head = '<tr><th rowspan="2">Место</th>'
if len(Venue_tour_id) > 1:
    table_head += '<th rowspan="2">Место на площадке</th><th rowspan="2">Площадка</th>'
table_head += f'<th rowspan="2">Команда</th><th rowspan="2">Сила команды</th><th colspan="{len(tour_names)}">Прогноз по вопросам турнира:</th></tr><tr>'
for nm in tour_names:
    table_head += f'<th rowspan="1">{nm}</th>'
            # <th rowspan="1">Nevermore-2 2022 (TrueDL 6.7)</th>
table_head += "</tr>\n"

# %%
ft = ft.replace("{{main_table_body}}", table_body)
ft = ft.replace("{{table_head}}", table_head)

# %%
# fo = open("test.html", "w", encoding="utf8")
# print(ft, file=fo)
# fo.close()

# %%
fo = open(f"Site/templates/predictions/{Venue_tour_id[0]}.html", "w", encoding="utf8")
print(ft, file=fo)
fo.close()
