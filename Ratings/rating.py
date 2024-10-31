from copy import deepcopy
import os
from scipy.stats import spearmanr
from datetime import datetime, timedelta, date
import json
import math
import sys
from tqdm import tqdm


sys.path.append('..')
sys.path.append('.')
from API.site_api_tools import ChGK_API_connector
#from API.site_api_tools import ChGK_API_connector
import sqlite3


MIN_QUESTION_RATING = 0
MAX_QUESTION_RATING = 10000
DELTA_MULTIPLIER = 3
NON_RATE_DELTA_MULTIPLIER = 0.1
INDEPNDENT_SKILL_QUESTION = 2000
PLAYER_START_RATING = 1000
TEAM_START_RATING = 1000
ELO_BASE = 10
ELO_NORM = 400
RATING_WEEK_DEGRADATION = 0.00



def ELO(R, Q, base = ELO_BASE, norm = ELO_NORM):
    try:
        return 1/(1+math.pow(base, (Q-R)/norm))
    except ArithmeticError:
        print("got erroror: ", R, Q, base, norm)
        raise("ssss")
    
def independed_ELO(R_list, Q = INDEPNDENT_SKILL_QUESTION, base = ELO_BASE, norm = ELO_NORM):
    p = 1
    for R in R_list:
        p *= ELO(Q, R)
    return (math.log(1/p - 1, base)*norm + Q) 
    

def ELO_estimate(R, rates, base = ELO_BASE, norm = ELO_NORM):
    return sum([ELO(R, r, base, norm) for r in rates])

def estimate_exact_prob(R, rates, base = ELO_BASE, norm = ELO_NORM):
    p = [0.0]*(len(rates)+2)
    p[0] = 1

    for i in range(len(rates)):
        pq = ELO(R, rates[i], base, norm)
        for j in range(i+2):
            p[i+1-j] = p[i+1-j] * (1-pq) + p[i-j] * pq
    return p[:-1]


def estimate_p_values(R, rates, N, base = ELO_BASE, norm = ELO_NORM):
    p = estimate_exact_prob(R, rates, base, norm)
    return (sum(p[:N+1]), sum(p[N:]))

def max_like(R, rates, gets, is_team = True, max_steps = 10000, eps = 0.00001, base = ELO_BASE, norm = ELO_NORM):
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
        if R > MAX_QUESTION_RATING:
            R = MAX_QUESTION_RATING
            break
        if R < MIN_QUESTION_RATING:
            R = MIN_QUESTION_RATING
            break
#    print("max_like: " + str(datetime.now() - start_time)+"   " + str(max_steps) + " " + str(step))
    return (R)

def calculate_score(places, ratings, rating_is_places = True):
    if not rating_is_places:
        ratings = [-x for x in ratings]
    return(spearmanr(places, ratings)) 

def calculate_NDCG(places, ratings, rating_is_places = True, soft_relevanse = True, worst_compared = True):
    perfect_places = sorted(places)
    worst_places = sorted(places, reverse=True)
    places_by_rating = sorted([x for x in range(len(ratings))], key=lambda x: ratings[x], reverse = (not rating_is_places)) #TODO: fix equal ratings
#    print(places_by_rating)
#    print(ratings)
    if soft_relevanse:
        perfect_score = sum([(1/math.log2(perfect_places[x]+1))/math.log2(x+2) for x in range(len(places))])
        worst_score = sum([(1/math.log2(worst_places[x]+1))/math.log2(x+2) for x in range(len(places))])
        my_score = sum([(1/math.log2(places[x]+1))/math.log2(places_by_rating[x]+2) for x in range(len(places))])
    else:
        perfect_score = sum([(1/perfect_places[x])/math.log2(x+2) for x in range(len(places))])
        worst_score = sum([(1/worst_places[x])/math.log2(x+2) for x in range(len(places))])
        my_score = sum([(1/places[x])/math.log2(places_by_rating[x]+2) for x in range(len(places))])
    print(perfect_score, my_score, worst_score)
    if perfect_score == 0:
        return math.nan
    if len(places) != len(ratings):
        return math.nan
    if perfect_score == worst_score:
        return math.nan
    if worst_compared:
        return((my_score-worst_score)/(perfect_score - worst_score)) 
    else:
        return((my_score)/(perfect_score)) 

def get_player_rating(connection, playerid, releaseid):
    rate = connection.execute('SELECT playerrating FROM playerratings WHERE playerid='+str(playerid)+' AND releaseid='+str(releaseid)).fetchone()
    if rate is None:
        return PLAYER_START_RATING
    else:
        return rate["playerrating"]


# def process_one_tournament_from_database(tournamentid, releaseid, connection, individual_questions = True, cleanup = True):
#     if cleanup:
#         connection.executescript('DELETE FROM playerratingsdelta WHERE tournamentid='+str(tournamentid))
#         connection.executescript('DELETE FROM tournamentratings WHERE tournamentid='+str(tournamentid))
#         connection.executescript('DELETE FROM questionrating WHERE tournamentid='+str(tournamentid))
#     start_time = datetime.now()
#     print(start_time)
#     question_gets = {}
#     local_teams_rates = []
#     question_values = []
#     team_ids = []
#     team_gets = {}
#     player_based_team_ratings = {}
#     team_players_id = {}
#     players_num = {}
#     total_gets = 0
    
#     max_qid = 0

#     Q_WARN  = True

#     tournament_result = connection.execute('SELECT teamid, mask, totalquestions FROM results WHERE tournamentid='+str(tournamentid)).fetchall()
    
#     for t in tournament_result:
#         qid = 0
#         if not t["teamid"] in team_gets:
#             team_gets[t["teamid"]] = 0

#         if individual_questions:
#             if t["mask"] == None:
#                 if Q_WARN:
#                     print("WARNING: No question data")#: " + str(t))
#                     Q_WARN = False
#                 continue
#             for q in t["mask"]:
#                 if not qid in question_gets:
#                     question_gets[qid] = 0
#                 if q == "1":
#                     question_gets[qid] += 1
#                     team_gets[t["team"]["id"]] += 1
#                 qid += 1
#         if max_qid < qid:
#             max_qid = qid

#         else:
#             if not "totalquestions" in t:
#                 continue
#             if t["totalquestions"] is None:
#                 continue
#             team_gets[t["teamid"]] = t["totalquestions"]
#             total_gets += t["totalquestions"]

#         #TODO: подумать про командный рейтинг
#         # if not t["teamid"] in teams_ratings:
#         #     teams_ratings[t["teamid"]] = TEAM_START_RATING
        
#     #roster
#     for rosterinfo in connection.execute('SELECT teamid, playerid FROM roster WHERE tournamentid='+str(tournamentid)).fetchall():
#         if not rosterinfo["teamid"] in team_players_id:
#             team_players_id[rosterinfo["teamid"]] = []
#         team_players_id[rosterinfo["teamid"]].append(rosterinfo["playerid"])
    
#     for teamid in team_players_id:
#         pl_rates = []
#         for playerid in team_players_id[teamid]:
#             pl_rates.append(get_player_rating(connection, playerid, releaseid))

#         players_num[teamid] = len(pl_rates)
#         if len(pl_rates) > 6:
#             player_based_team_ratings[teamid] = independed_ELO(sorted(pl_rates)[-6:], INDEPNDENT_SKILL_QUESTION)
#         else:
#             player_based_team_ratings[teamid] = independed_ELO(pl_rates, INDEPNDENT_SKILL_QUESTION)

#         local_teams_rates.append(player_based_team_ratings[teamid])
#         team_ids.append(teamid)
    
#     print("Data preparation: " + str(datetime.now() - start_time))
    
#     if individual_questions:
#         for q in range(max_qid):
#             question_values.append(max_like(1000, local_teams_rates, question_gets[q], False))
#     else:
#         qval = max_like(1000, local_teams_rates, total_gets/question_number, False)
#         for q in range(question_number):
#             question_values.append(qval)

#     team_delta = {}
#     player_delta = {}
#     for tm in team_ids:
#         team_delta[tm] = (team_gets[tm] - ELO_estimate(player_based_team_ratings[tm], question_values)) * DELTA_MULTIPLIER
#         w = 1.
#         if players_num[tm] > 6:
#             w = w*6 /players_num[tm]
#         for pl in team_players_id[tm]:
#             player_delta[pl] = team_delta[tm] * w
#     print("Totaly: " + str(datetime.now() - start_time))
#     return (player_based_team_ratings, question_values, player_delta)



def put_tournament_into_DB(tournamentid, tournament_result, connection): 
    roster_info = []
    results_info = []

    for t in tournament_result:
        for pl in t["teamMembers"]:
            roster_info.append((tournamentid, pl["player"]["id"], t["team"]["id"])) 
        if "current" in t:
            results_info.append((tournamentid, t["team"]["id"], t["position"], t["questionsTotal"], t["mask"], t["current"]["name"]))
        else:
            results_info.append((tournamentid, t["team"]["id"], t["position"], t["questionsTotal"], t["mask"], t["team"]["name"]))
    # print(roster_info)
    connection.cursor().executemany('INSERT INTO roster VALUES(?,?,?);',roster_info)        
    connection.cursor().executemany('INSERT INTO results VALUES(?,?,?,?,?,?);',results_info)
    connection.comit()           


def process_one_tournament(teams_ratings, tournament_result, players_rating, individual_questions = True, question_number = 36, tournament_weight = NON_RATE_DELTA_MULTIPLIER, players_rated_games_cnt = None, detailed_print = False, print_issues = False) : 
    
    issues = []
    
    start_time = datetime.now()
    if detailed_print:
        print("START TIME:", start_time)

    question_gets = {}
    local_teams_rates = []
    question_values = []
    team_gets = {}
    player_based_team_ratings = {}
    team_players_id = {}
    places = []
    players_num = {}
    total_gets = 0
    
    max_qid = 0

    Q_WARN  = True

    for t in tournament_result:

        pl_rates = []
        team_players_id[t["team"]["id"]] = []
        for pl in t["teamMembers"]:
            if pl["player"]["id"] not in players_rating:
                players_rating[pl["player"]["id"]] = PLAYER_START_RATING
            pl_rates.append(players_rating[pl["player"]["id"]])
            team_players_id[t["team"]["id"]].append(pl["player"]["id"])
        
        players_num[t["team"]["id"]] = len(pl_rates)

        if len(pl_rates) == 0:
            if print_issues:
                print("Team", t["team"]["id"], "has no players")
            player_based_team_ratings[t["team"]["id"]] = None
            issues.append((t["team"]["id"], "No players data"))
            continue

        if len(pl_rates) > 6:
            player_based_team_ratings[t["team"]["id"]] = independed_ELO(sorted(pl_rates)[-6:], INDEPNDENT_SKILL_QUESTION)
        else:
            player_based_team_ratings[t["team"]["id"]] = independed_ELO(pl_rates, INDEPNDENT_SKILL_QUESTION)


        qid = 0
        if not t["team"]["id"] in team_gets:
            team_gets[t["team"]["id"]] = 0

        if individual_questions:
            if t["mask"] is None:
                issues.append((t["team"]["id"], "No individual question data"))
                if Q_WARN:
                    if print_issues:
                        print("WARNING: No question data")#: " + str(t))
                    Q_WARN = False
                team_gets[t["team"]["id"]] = None
                # continue
            else:
                for q in t["mask"]:
                    if not qid in question_gets:
                        question_gets[qid] = 0
                    if q == "1":
                        question_gets[qid] += 1
                        team_gets[t["team"]["id"]] += 1
                    qid += 1
        else:
            if not "questionsTotal" in t:
                issues.append((t["team"]["id"], "No question data"))
                team_gets[t["team"]["id"]] = None
            elif t["questionsTotal"] is None:
                team_gets[t["team"]["id"]] = None
                issues.append((t["team"]["id"], "No question data"))
            elif t["questionsTotal"] == 0:
                if not "position" in t:
                    team_gets[t["team"]["id"]] = None
                    issues.append((t["team"]["id"], "No question data"))
                if t["position"] == 9999:
                    team_gets[t["team"]["id"]] = None
                    issues.append((t["team"]["id"], "No question data"))
            else:
                team_gets[t["team"]["id"]] = t["questionsTotal"]
                total_gets += t["questionsTotal"]

        # if not t["team"]["id"] in teams_ratings:
        #     teams_ratings[t["team"]["id"]] = TEAM_START_RATING
        

        places.append(t["position"])
        
        if not team_gets[t["team"]["id"]] is None:
            local_teams_rates.append(player_based_team_ratings[t["team"]["id"]])
        if max_qid < qid:
            max_qid = qid


    score = {}

    if detailed_print:
        print("Data preparation: " + str(datetime.now() - start_time))
    
    if individual_questions:
        total_gets = sum([question_gets[x] for x in question_gets])
        question_number = len(question_gets)
        Q_hardnes = max_like(1000, local_teams_rates, total_gets/question_number, False)
    
        for q in range(max_qid):
            question_values.append(max_like(1000, local_teams_rates, question_gets[q], False))
    else:
        qval = max_like(1000, local_teams_rates, total_gets/question_number, False)
        question_values = [qval]*question_number
        Q_hardnes = qval

    
    team_delta = {}
    player_delta = {}

    # print(team_gets, team_players_id)

    for tm in player_based_team_ratings:
        if player_based_team_ratings[tm] is None:
            continue
        if team_gets[tm] is None:
            team_delta[tm] = None    
        else:
            team_delta[tm] = (team_gets[tm] - ELO_estimate(player_based_team_ratings[tm], question_values)) * tournament_weight
            w = 1.
            if players_num[tm] > 6:
                w = w*6 /players_num[tm]
            
            for pl in team_players_id[tm]:
                if tournament_weight > NON_RATE_DELTA_MULTIPLIER:
                    if pl in players_rated_games_cnt:
                        if players_rated_games_cnt[pl] < 10:
                            wl = w*10/tournament_weight
                        elif players_rated_games_cnt[pl] < 20:
                            wl = w*7/tournament_weight
                        elif players_rated_games_cnt[pl] < 30:
                            wl = w*5/tournament_weight
                        else:
                            wl = w*3/tournament_weight

                    else:
                        wl = w*10/tournament_weight
                else:
                    wl = w
                
                player_delta[pl] = team_delta[tm] * wl

    # print("t", team_delta, player_delta)

    if detailed_print:
        print("Totaly: " + str(datetime.now() - start_time))
    
    return (player_based_team_ratings, question_values, player_delta, score, Q_hardnes, issues)

def season_to_date_string(seasone_num, for_comparison = False):
    season_dt = date.fromisoformat("2021-09-02") + timedelta(days=7*seasone_num+int(for_comparison))
    return season_dt.strftime("%Y-%m-%d")


def season_by_datestring(datestring) -> int:
    '''Return season/release id for date. Release 0 boundary is 2021-09-02 23:59:59'''
    return math.ceil((datetime.fromisoformat(datestring).date() - date.fromisoformat("2021-09-03")).days/7)

def season_by_datetime(date_value) -> int:
    '''Return season/release id for date. Release 0 boundary is 2021-09-02 23:59:59'''
    return math.ceil((date_value.date() - date.fromisoformat("2021-09-03")).days/7)



def process_all_data(SUB_DIR = "Output/TEST", start_from_release = 1):
    
    team_rates = {}
    player_ratings = {}
    players_rated_games_cnt = {}
    connector = ChGK_API_connector()
   
    save_data = True

    DBconn = sqlite3.connect(r'Output/rating.db')
    cursor = DBconn.cursor()
    
    if start_from_release > 1:
        players_rates = cursor.execute(f"SELECT playerid, playerrating FROM playerratings WHERE releaseid = {start_from_release-1}").fetchall()
        player_ratings = {x[0]:x[1] for x in players_rates}
        players_rated = cursor.execute(f"SELECT playerid, SUM(maii_rating) FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE tournaments.enddate < '{season_to_date_string(start_from_release-1,  True)}' and maii_rating=1 GROUP BY playerid").fetchall()
        players_rated_games_cnt = {x[0]:x[1] for x in players_rated}
    
    print("load cache")
    connector.load_cache("cache.pickle", from_pickle=True)
    all_issues = []

    print("reading tournaments_info")
    
    # tournaments_info_list = connector.get_all_rated_tournaments()
 
    with open('tournaments_info.json', 'r', encoding="utf8") as JSON:
        tournament_info_dict = json.load(JSON)


    minimal_end_date = season_to_date_string(start_from_release-1, True)

    ordered_tournament_ids = [t for t in tournament_info_dict if (tournament_info_dict[t]["dateEnd"] < "2024-11-08") and (tournament_info_dict[t]["dateEnd"] >= minimal_end_date)and(tournament_info_dict[t]["type"]["id"] != 5)]
    # ordered_tournament_ids = [t["id"] for t in tournaments_info_list if (t["dateEnd"] < "2022-10-11")and(t["type"]["id"] != 5)]
    ordered_tournament_ids.sort(key = lambda x: tournament_info_dict[x]["dateEnd"])

    # force_after = "2024-04-15"
    # force_after = "2024-06-15"

    # force_after = "2024-12-15"

    results = {}
    release_results = {start_from_release-1:{}, start_from_release:{}}
    release_results[start_from_release-1]["player_ratings"] = deepcopy(player_ratings)
    cnt = 0

    # release_date = datetime(year = 2013, month = 9, day = 5) 
    release_date = datetime(year = 2021, month = 9, day = 3) + timedelta(days=7*(start_from_release)) 
    release_num = start_from_release
    tournaments_by_reliases = [[]]

    print_datailes = False
  
    for t in tqdm(ordered_tournament_ids[:]):

        start = datetime.now()
        if print_datailes:
            print("Process tournament "+str(t)+ " start at "+str(start))
        
        data = connector.tournament_results(t, False)

        players_names = set()
        
        for tm in data:
            for pl in tm["teamMembers"]:
                if not pl["player"]["patronymic"]:
                    pl["player"]["patronymic"] = ""
                # print(pl["player"])
                players_names.add((pl["player"]["id"], pl["player"]["name"], pl["player"]["surname"], pl["player"]["patronymic"], pl["player"]["surname"] + " " + pl["player"]["name"] + " " + pl["player"]["patronymic"] ))



        if print_datailes:
            print("Data get took "+str(datetime.now() - start))
        cursor.executemany('INSERT OR IGNORE INTO players VALUES(?,?,?,?,?);',players_names)


        while not tournament_info_dict[t]["dateEnd"] < str(release_date):
            
            for pid in player_ratings:
                player_ratings[pid] -= RATING_WEEK_DEGRADATION*(player_ratings[pid] - PLAYER_START_RATING)
            
            records = []
            for tid in tournaments_by_reliases[-1]:
                
                for pid in results[tid]["delta_players"]:
                    if tournament_info_dict[t]["type"]["id"] != 5:
                        player_ratings[pid] += results[tid]["delta_players"][pid]
                    records.append((release_num, pid, results[tid]["delta_players"][pid], tid))
                    if "maiiRating" in tournament_info_dict[tid]:
                        if tournament_info_dict[tid]["maiiRating"]:
                            if not pid in players_rated_games_cnt:
                                players_rated_games_cnt[pid] = 0
                            players_rated_games_cnt[pid] += 1

            #insert multiple records in a single query
            # cursor.executemany('INSERT INTO playerratingsdelta VALUES(?,?,?,?);',records)

            release_results[release_num]["player_ratings"] = deepcopy(player_ratings)
            
            records = []
            for place, pid in enumerate(sorted(player_ratings, key=lambda x: -player_ratings[x])):
                records.append((release_num, pid, player_ratings[pid], place + 1))
                if not pid in release_results[release_num-1]["player_ratings"]:
                    records.append((release_num-1, pid, PLAYER_START_RATING, None))

            #insert multiple records in a single query
            cursor.executemany('INSERT INTO playerratings VALUES(?,?,?,?);',records)
            
            tournaments_by_reliases.append([])
            release_num += 1
            release_date += timedelta(days = 7)
            release_results[release_num] = {"release_date": str(release_date)}
            if print_datailes:
                print("Start working on release "+str(release_num)+":  "+str(release_date))
        
        questionQty = 0
        # print(tournament_info_dict[t]["questionQty"])
        for qqt in tournament_info_dict[t]["questionQty"]:
            questionQty += tournament_info_dict[t]["questionQty"][qqt]


        fulldata = [not (my_t["mask"] == None) for my_t in data] 

        if len(fulldata) > 0:
            individual = ((sum(fulldata)/len(fulldata)) > 0.75)
        else:
            individual = False 

        individual  = any(fulldata)

        if tournament_info_dict[t]["maiiRating"]:
            tournament_weight = DELTA_MULTIPLIER
        else:
            tournament_weight = NON_RATE_DELTA_MULTIPLIER
            
        delta, qv, delta_pl, score, Q_hardnes, issues = process_one_tournament(team_rates, data, player_ratings, individual, questionQty, tournament_weight, players_rated_games_cnt)

        all_issues += [(t, a, b) for a, b in issues]


        if save_data:
            q_diff = []
            q2_diff = []
            qvalues = [(t, i+1, qvl) for (i,qvl) in enumerate(qv)]
            tournamentrating_data = []
            results_data = []
            roster_data = []
            players_delta_rows = []
            legs_data = []
            # team_places = sorted([x for x in delta], key = lambda x: -delta[x])
            for my_t in data:
                if my_t["team"]["id"] in delta:
                    if (not delta[my_t["team"]["id"]] is None):
                # if ((not (my_t["mask"] == None)) |  (not (my_t["questionsTotal"] == None))) and (not delta[my_t["team"]["id"]] is None):
                    # if my_t["team"]["id"] in delta:
                        atmost, atleast = estimate_p_values(delta[my_t["team"]["id"]], qv, my_t["questionsTotal"]) if (not (my_t["questionsTotal"] == None)) else (None, None)
                        team_perf = max_like(1000, qv, my_t["questionsTotal"]) if (not (my_t["questionsTotal"] == None)) else None
                        tournamentrating_data.append((t, my_t["team"]["id"], delta[my_t["team"]["id"]], ELO_estimate(delta[my_t["team"]["id"]], qv), atleast, atmost, team_perf))
                        results_data.append((t, my_t["team"]["id"], my_t["position"], my_t["questionsTotal"], my_t["mask"], my_t["current"]["name"]))
                        for pld in my_t["teamMembers"]:
                            roster_data.append((t, pld["player"]["id"], my_t["team"]["id"]))
                            if pld["player"]["id"] in delta_pl:
                                players_delta_rows.append((release_num, pld["player"]["id"], delta_pl[pld["player"]["id"]], t, my_t["team"]["id"]))
                            else:
                                players_delta_rows.append((release_num, pld["player"]["id"], None, t, my_t["team"]["id"]))

                        # q_diff.append(abs(my_t["questionsTotal"] - ELO_estimate(delta[my_t["team"]["id"]], qv)))
                        # q2_diff.append((my_t["questionsTotal"] - ELO_estimate(delta[my_t["team"]["id"]], qv))**2)
                    q_last = 0
                    
                    if (not my_t["mask"] is None) and (not delta[my_t["team"]["id"]] is None):
                        for qqt in sorted(tournament_info_dict[t]["questionQty"], key=lambda x: int(x)):
                            leg_N = tournament_info_dict[t]["questionQty"][qqt]
                            q_cur = q_last + leg_N
                            leg_Total = sum([x=="1" for x in  my_t["mask"][q_last:q_cur]])
                            atmost, atleast = estimate_p_values(delta[my_t["team"]["id"]], qv[q_last:q_cur], leg_Total)

                            legs_data.append((t, my_t["team"]["id"], int(qqt), leg_N, my_t["mask"][q_last:q_cur],leg_Total, ELO_estimate(delta[my_t["team"]["id"]], qv[q_last:q_cur]), atleast, atmost))
                            q_last = q_cur
                            # bytes = f.write(my_t["current"]["name"] + "; " +str(delta[my_t["team"]["id"]])+ "; " +str(len(my_t["teamMembers"])) +"; "+ str(my_t["position"]) + "; " + str(team_places.index(my_t["team"]["id"])+1)+"; " + str(my_t["questionsTotal"]) + "; " + str(ELO_estimate(delta[my_t["team"]["id"]], qv))+"\n")
            
        cursor.executemany('INSERT INTO questionrating VALUES(?,?,?);',qvalues)            
        cursor.executemany('INSERT INTO roster VALUES(?,?,?);',roster_data)        
        cursor.executemany('INSERT INTO tournamentratings VALUES(?,?,?,?,?,?,?);',tournamentrating_data)    
        cursor.executemany('INSERT INTO results VALUES(?,?,?,?,?,?);',results_data)        
        cursor.executemany('INSERT INTO tournaments_legs VALUES(?,?,?,?,?,?,?,?,?);',legs_data)        
        cursor.executemany('INSERT INTO playerratingsdelta VALUES(?,?,?,?,?);', players_delta_rows)    

        
        # print(tournament_info_dict[t])
        cursor.execute("INSERT OR REPLACE INTO tournaments VALUES(?,?,?,?,?,?,?,?,?);", (tournament_info_dict[t]["id"],tournament_info_dict[t]["name"], tournament_info_dict[t]["dateStart"],tournament_info_dict[t]["dateEnd"], tournament_info_dict[t]["type"]["id"], tournament_info_dict[t]["type"]["name"], tournament_info_dict[t]["maiiRating"], Q_hardnes, tournament_info_dict[t]["longName"]))

        results[t] = {}
        results[t]["qv"] = qv
        results[t]["delta_players"] = delta_pl
        results[t]["team_rates"] = delta

        # results[t]["score"] = score
        # results[t]["SSE"] = sum(q2_diff)
        # results[t]["SAE"] = sum(q_diff)

        # if len(q_diff) >0:
        #     results[t]["MSE"] = sum(q2_diff)/len(q2_diff)
        #     results[t]["MAE"] = sum(q_diff)/len(q_diff)
        # else:
        #     results[t]["MSE"] = 0
        #     results[t]["MAE"] = 0
        
        tournaments_by_reliases[-1].append(t)
    #    for pl in delta_pl:
    #        player_ratings[pl] += delta_pl[pl]
        cnt += 1
    
    records = []
    for tid in tournaments_by_reliases[-1]:
        for pid in results[tid]["delta_players"]:
            player_ratings[pid] += results[tid]["delta_players"][pid]
            records.append((release_num, pid, results[tid]["delta_players"][pid], tid))

    #insert multiple records in a single query
    # cursor.executemany('INSERT INTO playerratingsdelta VALUES(?,?,?,?);',records)    

    release_results[release_num]["player_ratings"] = deepcopy(player_ratings)
    
    records = []
    for place, pid in enumerate(sorted(player_ratings, key=lambda x: -player_ratings[x])):
        records.append((release_num, pid, player_ratings[pid], place+1))
        if not pid in release_results[release_num-1]["player_ratings"]:
            records.append((release_num-1, pid, PLAYER_START_RATING, None))


    cursor.executemany('INSERT INTO playerratings VALUES(?,?,?,?);',records)

    DBconn.commit()
    DBconn.close()

    
    #Предполагаем, что кэш больше не обновляется, все его изиенения в отдельных процессах/блоках
    #print("Save chach. Be patient")
    
    #connector.save_cache("cache.json")


    with open("issues.json", "w") as file:
        json.dump(all_issues, file)

    
    # connector.save_cache("cache_large.json")
    # print("Done")
    ## Models comparison

    # WB = 0
    # WC = 0
    # D = 0
    # NWB = 0
    # NWC = 0
    # ND = 0

    # ordered_tournament_ids[-3:]

    # for t in ordered_tournament_ids[-150:]:
    #     print(t, results[t]["score"]["NDCG"]["B"], results[t]["score"]["NDCG"]["C"])


    # for t in ordered_tournament_ids[-150:]:
    #     print(results[t]["score"]["spearman"]["B"][0], results[t]["score"]["spearman"]["C"][0])
    #     if results[t]["score"]["spearman"]["B"][0] > results[t]["score"]["spearman"]["C"][0]: WB += 1
    #     if results[t]["score"]["spearman"]["B"][0] < results[t]["score"]["spearman"]["C"][0]: WC += 1
    #     if results[t]["score"]["spearman"]["B"][0] == results[t]["score"]["spearman"]["C"][0]: D += 1
    #     if results[t]["score"]["NDCG"]["B"] > results[t]["score"]["NDCG"]["C"]: NWB += 1
    #     if results[t]["score"]["NDCG"]["B"] < results[t]["score"]["NDCG"]["C"]: NWC += 1
    #     if results[t]["score"]["NDCG"]["B"] == results[t]["score"]["NDCG"]["C"]: ND += 1

    # print(WB, WC, D)
    # print(NWB, NWC, ND)

    # trnm_list = [9207, 9693, 9737, 9423,  9543, 9582, 9205, 9493, 9147, 9626]
    # for trnm in trnm_list:
    #     print(trnm, results[trnm]["SAE"], results[trnm]["SSE"])
    # print("Total:", sum([results[trnm]["SAE"] for trnm in trnm_list]), sum([results[trnm]["SSE"] for trnm in trnm_list]))
    # with open(SUB_DIR+"/results.json", "w") as file:
    #     json.dump(results, file)

    # with open(SUB_DIR+"/release_results.json", "w") as file:
    #     json.dump(release_results, file)



def clear_db(start_from_release = 0):
    #try to clear all data
    conn = sqlite3.connect(r'Output/rating.db')
#     try:
#         conn.executescript('''
#         CREATE TABLE tournaments ( tournamentid integer primary key, name varchar(255), startdate date, enddate date, typeoft_id INTEGER, type TEXT); 
#         CREATE TABLE roster ( tournamentid integer, playerid integer, teamid integer ); 
#         CREATE TABLE results ( tournamentid integer, teamid integer, place real, totalquestions integer, mask varchar(255), teamname varchar(255));
#         CREATE TABLE releases ( releaseid integer primary key, relisdate date);
#         CREATE TABLE playerratings ( releaseid integer, playerid integer, playerrating real, place integer);
#         CREATE TABLE playerratingsdelta ( releaseid integer, playerid integer, deltarating real, tournamentid integer);
#         CREATE TABLE tournamentratings ( tournamentid integer, teamid integer, teamrating real, teamperformance real, predictedquestions real, atleastprob real, atmostprob real);
#         CREATE TABLE players ( playerid integer primary key, name varchar(255), surname varchar(255), patronim varchar(255), fullname varchar(255));
#         CREATE TABLE questionrating ( tournamentid int, questionid int, hardnes real);
#         CREATE TABLE teams ( teamid integer primary key, teamname varchar(255));
#         CREATE TABLE tournaments_legs (tournamentid integer, teamid integer, leg integer, legsize integer, mask varchar(255), legquestions integer, predictedquestions real, atleastprob real, atmostprob real); 
# ''')
#         conn.close()  
#     except Exception:
        # print("DB exists?")
    print("Clear DB:")
    cursor = conn.cursor()
    if start_from_release == 0:
        cursor.execute('DELETE FROM tournaments;')
        cursor.execute('DELETE FROM roster;')
        cursor.execute('DELETE FROM results;')
        cursor.execute('DELETE FROM releases;')
        cursor.execute('DELETE FROM playerratings;')
        cursor.execute('DELETE FROM playerratingsdelta;')
        cursor.execute('DELETE FROM tournamentratings;')
        cursor.execute('DELETE FROM players;')
        cursor.execute('DELETE FROM questionrating;')
        cursor.execute('DELETE FROM teams;')
        cursor.execute('DELETE FROM tournaments_legs;')
    else:
        print("    playerratings")        
        cursor.execute(f'DELETE FROM playerratings WHERE releaseid >= {start_from_release};')
        print("    playerratingsdelta")        
        cursor.execute(f'DELETE FROM playerratingsdelta WHERE ROWID IN (SELECT playerratingsdelta.ROWID FROM playerratingsdelta JOIN tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE enddate >= "{season_to_date_string(start_from_release-1, True)}");')
        print("    roster")        
        cursor.execute(f'DELETE FROM roster WHERE ROWID IN (SELECT roster.ROWID FROM roster JOIN tournaments ON roster.tournamentid=tournaments.tournamentid WHERE enddate >= "{season_to_date_string(start_from_release-1, True)}");')
        print("    tournamentratings")        
        cursor.execute(f'DELETE FROM tournamentratings WHERE ROWID IN (SELECT tournamentratings.ROWID FROM tournamentratings JOIN tournaments ON tournamentratings.tournamentid=tournaments.tournamentid WHERE enddate >= "{season_to_date_string(start_from_release-1, True)}");')
        print("    questionrating")        
        cursor.execute(f'DELETE FROM questionrating WHERE ROWID IN (SELECT questionrating.ROWID FROM questionrating JOIN tournaments ON questionrating.tournamentid=tournaments.tournamentid WHERE enddate >= "{season_to_date_string(start_from_release-1, True)}");')
        print("    results")        
        cursor.execute(f'DELETE FROM results WHERE ROWID IN (SELECT results.ROWID FROM results JOIN tournaments ON results.tournamentid=tournaments.tournamentid WHERE enddate >= "{season_to_date_string(start_from_release-1, True)}");')
        print("Clear DB DONE")        

    conn.commit()
    conn.close()



def update_tournaments():
    connector = ChGK_API_connector()
    connector.load_cache("cache.pickle", from_pickle=True)
    with open("tournaments_info.json", "r") as file:
        tournaments_info_dict = json.load(file)
    last_updated = max(tournaments_info_dict[t]["lastEditDate"] for t in tournaments_info_dict)
    updated = last_updated[:10]
    print("Tournament update from", updated)
    test_new = connector.get_all_tournaments(startdate_after="2021-09-01", last_edit_date=updated)
    for t in tqdm(test_new):
        rs = connector.tournament_results(t["id"], True)
        tournaments_info_dict[str(t["id"])] = t
    ordered_changes = sorted([(x["id"], x["name"], x["lastEditDate"], x["dateEnd"]) for x in test_new if x["dateEnd"] < "2024-11-01"], key=lambda x: x[3])  
    print("Earliest updated tournament", ordered_changes[0])
    connector.save_cache("cache.pickle", to_pickle=True)
    with open("tournaments_info.json", "w") as file:
        json.dump(tournaments_info_dict, file)
    datestr = ordered_changes[0][3]
    earliest_release = season_by_datestring(datestr)
    return(earliest_release)

def update_team_ratings(actual_release = 0):
    conn = sqlite3.connect(r'Output/rating.db')
    my_rost_value = conn.execute(f"SELECT base_roster.teamid as teamid, base_roster.player_id, playerratings.playerrating FROM base_roster INNER JOIN playerratings ON base_roster.player_id = playerratings.playerid AND playerratings.releaseid = {actual_release} ORDER BY teamid").fetchall()
    all_rates = []
    team_id = 0
    loc_rates = []
    for pl in my_rost_value+[(0,0,0)]:
        if pl[0] != team_id:
            if len(loc_rates)>0:
                all_rates.append((team_id, independed_ELO(sorted(loc_rates)[-6:], INDEPNDENT_SKILL_QUESTION)))
            loc_rates = [pl[2]]
            team_id = pl[0]
        else:
            loc_rates.append(pl[2])
    conn.executemany('INSERT INTO base_team_rates VALUES(?,?);',all_rates)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    actual_release = season_by_datetime(datetime.now())
    start_from_release = update_tournaments()
    clear_db(start_from_release = start_from_release)
    process_all_data(start_from_release = start_from_release)
    update_team_ratings(actual_release)
    #TODO: copy db

    import shutil

    try:
        shutil.copyfile('Output/rating.db', 'Output/rating_for_site.db')
    except Exception:
        shutil.copyfile('Output/rating.db', 'Output/rating_for_site.db')
