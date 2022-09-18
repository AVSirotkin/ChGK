from datetime import datetime
import json
import math
import sys
import json
sys.path.append('./API/')
from site_api_tools import ChGK_API_connector

MIN_QUESTION_RATING = 0
MAX_QUESTION_RATING = 10000
DELTA_MULTIPLIER = 20
INDEPNDENT_SKILL_QUESTION = 2000
PLAYER_START_RATING = 1000
TEAM_START_RATING = 1000





def ELO(R, Q, base = 10, norm = 400):
    return 1/(1+math.pow(10, (Q-R)/norm))

def independed_ELO(R_list, Q, base = 10, norm = 400):
    p = 1
    for R in R_list:
        p *= ELO(Q, R)
    return (math.log(1/p - 1, base)*norm + Q) 
    

def ELO_estimate(R, rates, base = 10, norm = 400):
    return sum([ELO(R, r, base, norm) for r in rates])

def max_like(R, rates, gets, is_team = True, max_steps = 10000, eps = 0.00001, base = 10, norm = 400):
#    start_time = datetime.now()
    step = R*0.34
    N = len(rates)
    if type(gets) == list:
        if is_team:
            result = sum(gets)
        else: 
            result = N - sum(gets)
    else:
        if is_team:
            result = gets
        else: 
            result = N - gets
        
    prev_increase = False
    
    if result == N: return MAX_QUESTION_RATING
    if result == 0: return MIN_QUESTION_RATING
    
    while (step > eps) and (max_steps > 0):
        max_steps -= 1
        prognosys = ELO_estimate(R, rates, base, norm)
        
        if prognosys > result:
            if prev_increase:
                step /= 2
            prev_increase = False
            R -= step
        else:
            if not prev_increase:
                step /= 2
            prev_increase = True
            R += step
#    print("max_like: " + str(datetime.now() - start_time)+"   " + str(max_steps) + " " + str(step))
    return (R)

def process_one_tournament(teams_ratings, tournament_result, players_rating): 
    start_time = datetime.now()
    print(start_time)
    question_gets = {}
    local_teams_rates = []
    question_values = []
    team_ids = []
    team_gets = {}
    player_based_team_ratings = {}
    team_players_id = {}

    max_qid = 0
    for t in tournament_result:
        qid = 0
        if t["mask"] == None:
            continue
        if not t["team"]["id"] in team_gets:
            team_gets[t["team"]["id"]] = 0

        for q in t["mask"]:
            if not qid in question_gets:
                question_gets[qid] = 0
            if q == "1":
                question_gets[qid] += 1
                team_gets[t["team"]["id"]] += 1
            qid += 1
        if not t["team"]["id"] in teams_ratings:
            teams_ratings[t["team"]["id"]] = TEAM_START_RATING
        
        pl_rates = []
        team_players_id[t["team"]["id"]] = []
        for pl in t["teamMembers"]:
            if pl["player"]["id"] not in players_rating:
                players_rating[pl["player"]["id"]] = PLAYER_START_RATING
            pl_rates.append(players_rating[pl["player"]["id"]])
            team_players_id[t["team"]["id"]].append(pl["player"]["id"])
        
        player_based_team_ratings[t["team"]["id"]] = independed_ELO(pl_rates, INDEPNDENT_SKILL_QUESTION)
               
        local_teams_rates.append(player_based_team_ratings[t["team"]["id"]])
        team_ids.append(t["team"]["id"])
        if max_qid < qid:
            max_qid = qid
    
    print("Data preparation: " + str(datetime.now() - start_time))
    
#    print(player_based_team_ratings)
    for q in range(max_qid):
        question_values.append(max_like(1000, local_teams_rates, question_gets[q], False))
    team_delta = {}
    player_delta = {}
    for tm in team_ids:
        team_delta[tm] = (team_gets[tm] - ELO_estimate(player_based_team_ratings[tm], question_values)) * DELTA_MULTIPLIER
        for pl in team_players_id[tm]:
            player_delta[pl] = team_delta[tm]
    print("Totaly: " + str(datetime.now() - start_time))
    return (player_based_team_ratings, question_values, player_delta)



team_rates = {}
player_ratings = {}
connector = ChGK_API_connector()

connector.load_cache("cache.json")

with open('tournaments.json', 'r', encoding="utf8") as JSON:
    tournaments_info_list = json.load(JSON)

tournament_info_dict = {}
for t in tournaments_info_list:
    tournament_info_dict[t["id"]] = t

ordered_tournament_ids = [t["id"] for t in tournaments_info_list if t["dateEnd"] < "2022-09-01"]
ordered_tournament_ids.sort(key = lambda x: tournament_info_dict[x]["dateEnd"])

results = {}

cnt = 0
for t in ordered_tournament_ids[:]:
    start = datetime.now()
    print("Process tournament "+str(t)+ " start at "+str(start))
    data = connector.tournament_results(t)
    print("Data get took "+str(datetime.now() - start))

    delta, qv, delta_pl = process_one_tournament(team_rates, data, player_ratings)
    results[t] = {}
    results[t]["qv"] = qv
    results[t]["delta_players"] = delta_pl
    results[t]["team_rates"] = delta
    
    for pl in delta_pl:
        player_ratings[pl] += delta_pl[pl]
    cnt += 1
#    if cnt % 10 == 0:
#        connector.save_cache("cache.json")
    

#connector.save_cache("cache.json")


#with open("players_01.json", "w") as file:
#    json.dump(player_ratings, file)

#with open("results.json", "w") as file:
#    json.dump(results, file)



#data = connector.tournament_results(7723)
#delta, qv, delta_pl = process_one_tournament(team_rates, data, player_ratings)
 
#pl_list = [pl for pl in player_ratings]
#pl_list.sort(key=lambda x: player_ratings[x])

#pl_list[-10:]


#for t in results:
#    if 81677 in results[t]["delta_players"]:
#        print(t, results[t]["delta_players"][81677])


#for t in results:
#    if 4121 in results[t]["delta_players"]:
#        print(t, results[t]["delta_players"][4121])
