import sys
sys.path.append('./API/')
from site_api_tools import ChGK_API_connector

connector = ChGK_API_connector()


connector.load_cache("cache.json")

All_tournaments_dict = {}
all_teams =  [84107, 75486]#, 72752]#+[83813, 71559, 83361, 59319, 67894, 59711, 83249]

for tm in all_teams:
    All_tournaments_dict[tm] = connector.get_all_tournaments_id_for_team(tm)

all_comparison = {}

for TeamA_id in all_teams:
    for TeamB_id in all_teams:
        Tournaments_list = [t for t in All_tournaments_dict[TeamA_id] if t in All_tournaments_dict[TeamB_id]]
        win = 0
        draw = 0
        lose = 0
        win_list = []
        draw_list = []
        lose_list = []
        for t in Tournaments_list[:]:
            results = connector.tournament_results(t)
            for res in results:
                if str(res['team']["id"]) == str(TeamA_id):
                    team_A_result = res
                if str(res['team']["id"]) == str(TeamB_id):
                    team_B_result = res
#            print(t)
            if ("position" in team_A_result) & ("position" in team_B_result):#(team_A_result["rating"] != None)&(team_B_result["rating"] != None):
                if (team_A_result["position"]!=None) & (team_B_result["position"] != None):# (team_A_result["rating"]["inRating"]) & (team_B_result["rating"]["inRating"]):
                    place_A = float(team_A_result["position"]) 
                    place_B = float(team_B_result["position"]) 
                    if place_A < place_B:
                        win += 1
                        win_list.append(t)
                    elif place_A > place_B:
                        lose += 1
                        lose_list.append(t)
                    else:
                        draw += 1
                        draw_list.append(t)
        print(win, draw, lose)
        if TeamA_id not in all_comparison:
            all_comparison[TeamA_id] = {}
        all_comparison[TeamA_id][TeamB_id] = {}
        all_comparison[TeamA_id][TeamB_id]["win"] = win
        all_comparison[TeamA_id][TeamB_id]["win_list"] = win_list
        all_comparison[TeamA_id][TeamB_id]["lose"] = lose
        all_comparison[TeamA_id][TeamB_id]["lose_list"] = lose_list
        all_comparison[TeamA_id][TeamB_id]["draw"] = draw
        all_comparison[TeamA_id][TeamB_id]["draw_list"] = draw_list

connector.save_cache("cache.json")

import json
with open('all_compare.json', 'w') as f:
    json.dump(all_comparison, f)

f = open("comparison.csv", "w")
f.write(" ," + ",".join([str(i) for i in all_teams])+"\n")
for i in all_teams:
    s = ""
    s += str(i)
    for j in all_teams:
        s +=", "+str(all_comparison[i][j]["win"])+":"+str(all_comparison[i][j]["draw"])+":"+str(all_comparison[i][j]["lose"])
    f.write(s+"\n")
f.close()
