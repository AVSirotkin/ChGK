from turtle import color
from scipy.stats import spearmanr
from datetime import datetime
import json
import math
import sys
import json
sys.path.append('./API/')
from site_api_tools import ChGK_API_connector

MIN_QUESTION_RATING = 0
MAX_QUESTION_RATING = 10000
DELTA_MULTIPLIER = 10
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

def calculate_score(places, ratings, rating_is_places = True):
    if not rating_is_places:
        ratings = [-x for x in ratings]
    return(spearmanr(places, ratings)) 

def calculate_NDCG(places, ratings, rating_is_places = True):
    perfect_places = sorted(places)
    places_by_rating = sorted([x for x in range(len(ratings))], key=lambda x: ratings[x], reverse = (not rating_is_places)) #TODO: fix equal ratings
#    print(places_by_rating)
#    print(ratings)
    perfect_score = sum([(1/perfect_places[x])/math.log2(x+2) for x in range(len(places))])
    my_score = sum([(1/places[x])/math.log2(places_by_rating[x]+2) for x in range(len(places))])
    if perfect_score == 0:
        return math.nan
    return(my_score/perfect_score) 



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
    places = []
    B_predicted_places = []
    
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

        places.append(t["position"])

        if "rating" in t:
            if t["rating"] != None:
                if "predictedPosition" in t["rating"]:
                    B_predicted_places.append(t["rating"]["predictedPosition"])
                else:
                    B_predicted_places.append(10000)
                    print("WARNING: no predictedPosition in rating: " + str(t) )
            else:
                B_predicted_places.append(10000)
                print("WARNING: rating is empty:  " + str(t) )
        else:
            B_predicted_places.append(10000)
            print("WARNING: no rating: " + str(t) )
        
        local_teams_rates.append(player_based_team_ratings[t["team"]["id"]])
        team_ids.append(t["team"]["id"])
        if max_qid < qid:
            max_qid = qid
    score = {}
    score["spearman"] = {}
    score["spearman"]["B"] = calculate_score(places, B_predicted_places, True) 
    score["spearman"]["C"] = calculate_score(places, local_teams_rates,False)
    score["NDCG"] = {}
    score["NDCG"]["B"] = calculate_NDCG(places, B_predicted_places, True) 
    score["NDCG"]["C"] = calculate_NDCG(places, local_teams_rates, False)


    print("Score B: "+str(score["spearman"]["B"]) + "  Score C: "+str(score["spearman"]["C"]))
    print("NDCG B: "+str(score["NDCG"]["B"]) + "  NDCG C: "+str(score["NDCG"]["C"]))

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
    return (player_based_team_ratings, question_values, player_delta, score)



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

    delta, qv, delta_pl, score = process_one_tournament(team_rates, data, player_ratings)
    results[t] = {}
    results[t]["qv"] = qv
    results[t]["delta_players"] = delta_pl
    results[t]["team_rates"] = delta
    results[t]["score"] = score
    
    for pl in delta_pl:
        player_ratings[pl] += delta_pl[pl]
    cnt += 1

## Models comparison

WB = 0
WC = 0
D = 0
NWB = 0
NWC = 0
ND = 0
for t in ordered_tournament_ids[-122:]:
    if results[t]["score"]["spearman"]["B"][0] > results[t]["score"]["spearman"]["C"][0]: WB += 1
    if results[t]["score"]["spearman"]["B"][0] < results[t]["score"]["spearman"]["C"][0]: WC += 1
    if results[t]["score"]["spearman"]["B"][0] == results[t]["score"]["spearman"]["C"][0]: D += 1
    if results[t]["score"]["NDCG"]["B"] > results[t]["score"]["NDCG"]["C"]: NWB += 1
    if results[t]["score"]["NDCG"]["B"] < results[t]["score"]["NDCG"]["C"]: NWC += 1
    if results[t]["score"]["NDCG"]["B"] == results[t]["score"]["NDCG"]["C"]: ND += 1

print(WB, WC, D)

print(NWB, NWC, ND)



player_ratings[4121]
player_ratings[115199]
player_ratings[76084]
