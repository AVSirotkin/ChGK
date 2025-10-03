from copy import deepcopy
import os
from scipy.stats import spearmanr
from datetime import datetime, timedelta, date
import json
import math
import sys
from tqdm import tqdm
import logging
from scipy.stats import rankdata
import configparser

logger = logging.getLogger(__name__)

sys.path.append('..')
sys.path.append('.')
from API.site_api_tools import ChGK_API_connector
#from API.site_api_tools import ChGK_API_connector
import sqlite3

from memory_profiler import profile

MIN_QUESTION_RATING = 0
MAX_QUESTION_RATING = 10000
DELTA_MULTIPLIER = 3
# NON_RATE_DELTA_MULTIPLIER = 1
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


def put_tournament_results_into_DB(tournamentid, tournament_result, connection): 
    
    roster_info = []
    results_info = []
    team_names = []

    players_names = set()
    
    for tm in tournament_result:
        for pl in tm["teamMembers"]:
            roster_info.append((tournamentid, pl["player"]["id"], tm["team"]["id"])) 
            if not pl["player"]["patronymic"]:
                pl["player"]["patronymic"] = ""
            # print(pl["player"])
            players_names.add((pl["player"]["id"], pl["player"]["name"], pl["player"]["surname"], pl["player"]["patronymic"], pl["player"]["surname"] + " " + pl["player"]["name"] + " " + pl["player"]["patronymic"] ))
        team_names.append((tm["team"]["id"], tm["team"]["name"]))
        if "current" in tm:
            results_info.append((tournamentid, tm["team"]["id"], tm["position"], tm["questionsTotal"], tm["mask"], tm["current"]["name"]))
        else:
            results_info.append((tournamentid, tm["team"]["id"], tm["position"], tm["questionsTotal"], tm["mask"], tm["team"]["name"]))


    connection.executemany('INSERT OR REPLACE INTO players VALUES(?,?,?,?,?);',players_names)
    connection.commit()


    connection.execute(f'DELETE FROM results WHERE tournamentid = {tournamentid};')
  
    
    # print(roster_info)
    connection.execute(f'DELETE FROM roster WHERE tournamentid = {tournamentid};')
    
    connection.executemany('INSERT INTO roster VALUES(?,?,?);',roster_info)        
    
    connection.executemany('INSERT INTO results VALUES(?,?,?,?,?,?);',results_info)
  
    connection.executemany('INSERT OR REPLACE INTO teams VALUES(?, ?);',team_names)

    connection.commit()           


def process_one_tournament_from_DB(DB, tournamentid, players_rating, individual_questions = True, question_number = 36, tournament_weight = NON_RATE_DELTA_MULTIPLIER, players_rated_games_cnt = None, detailed_print = False, print_issues = False) : 
    
    issues = []
    start_time = datetime.now()
    if detailed_print:
        print("START TIME:", start_time, tournamentid)
    logger.debug(f"Process {tournamentid}")
    question_gets = {}
    question_attempts = {}
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
    individual_data = DB.execute(f"SELECT teamid from data.results WHERE tournamentid =={tournamentid} and mask IS NOT NULL").fetchall()
    if len(individual_data) == 0:
        individual_questions = False
    
    team_rosters_sql = DB.execute(f"SELECT teamid, playerid FROM data.roster WHERE tournamentid =={tournamentid}").fetchall()
    # print("rost:", team_rosters_sql)
    for pl in team_rosters_sql:
        if pl[0] not in team_players_id:
            team_players_id[pl[0]] = [pl[1]]
        else:
            team_players_id[pl[0]] += [pl[1]]

    for tid in team_players_id:
        pl_rates = [(players_rating[pid] if pid in players_rating else PLAYER_START_RATING) for pid in team_players_id[tid]]
        players_num[tid] = len(pl_rates)
        if len(team_players_id[tid]) > 6:
            player_based_team_ratings[tid] = independed_ELO(sorted(pl_rates)[-6:], INDEPNDENT_SKILL_QUESTION)
        else:
            player_based_team_ratings[tid] = independed_ELO(pl_rates, INDEPNDENT_SKILL_QUESTION)

    team_results_sql = DB.execute(f"SELECT teamid, totalquestions, mask, place FROM results WHERE tournamentid =={tournamentid}").fetchall()
    # print("res:", team_results_sql)
    for tm in team_results_sql:
        if not tm[0] in player_based_team_ratings:
            player_based_team_ratings[tm[0]] = None
            continue
        # print(tm)
        if individual_questions:
            if tm[2] is None:
                issues.append((tm[0], "No individual question data"))
                if Q_WARN:
                    if print_issues:
                        print("WARNING: No question data")#: " + str(t))
                    Q_WARN = False
                team_gets[tm[0]] = None
                # continue
            else:
                team_gets[tm[0]] = 0
                for i, q in enumerate(tm[2]):
                    qid = i + 1
                    if not qid in question_gets:
                        question_gets[qid] = 0
                        question_attempts[qid] = []
                    
                    if q == "1":
                        question_gets[qid] += 1
                        team_gets[tm[0]] += 1
                        question_attempts[qid].append(player_based_team_ratings[tm[0]])
                    if (q == "0")|(q == "?"):
                        question_attempts[qid].append(player_based_team_ratings[tm[0]])
        else:
            if tm[1] is None:
                issues.append((tm[0], "No question data"))
                team_gets[tm[0]] = None
            elif tm[1] == 0:
                if tm[3] == 9999:
                    team_gets[tm[0]] = None
                    issues.append((tm[0], "No question data"))
                else:
                    team_gets[tm[0]] = 0
                    
            else:
                team_gets[tm[0]] = tm[1]
                total_gets += tm[1]
    # print("tg", team_gets)
    local_teams_rates = [player_based_team_ratings[tid] for tid in player_based_team_ratings if not player_based_team_ratings[tid] is None]
    
    score = {}
    if detailed_print:
        print("Data preparation: " + str(datetime.now() - start_time))
    
    if individual_questions:
        # print(question_gets)
        total_gets = sum([question_gets[x] for x in question_gets])
        question_number = len(question_gets)
        Q_hardnes = max_like(1000, local_teams_rates, total_gets/question_number, False) #TODO: Сделать индивидуальный обход вопросов 
    
        for q in question_gets:
            question_values.append(max_like(1000, local_teams_rates, question_gets[q], False)) #TODO: Сделать индивидуальный обход вопросов (частично снятый)
    else:
        if question_number > 0:
            qval = max_like(1000, local_teams_rates, total_gets/question_number, False)
        else:
            qval = 0
        question_values = [qval]*question_number
        Q_hardnes = qval

    # print("============")    
    # print("qv", question_values)    

    # print("============")    
    # print(tournamentid)


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

    # print("t", tournamentid, team_delta, player_delta)

    if detailed_print:
        print("Totaly: " + str(datetime.now() - start_time))
    
    return (player_based_team_ratings, question_values, player_delta, score, Q_hardnes, issues)

####
## Temporaly commented due to many difference with process_one_tournament_from_DB thats currently onli actual
####
# def process_one_tournament(teams_ratings, tournament_result, players_rating, individual_questions = True, question_number = 36, tournament_weight = NON_RATE_DELTA_MULTIPLIER, players_rated_games_cnt = None, detailed_print = False, print_issues = False) : 
    
#     issues = []
    
#     start_time = datetime.now()
#     if detailed_print:
#         print("START TIME:", start_time)

#     question_gets = {}
#     local_teams_rates = []
#     question_values = []
#     team_gets = {}
#     player_based_team_ratings = {}
#     team_players_id = {}
#     places = []
#     players_num = {}
#     total_gets = 0
    
#     max_qid = 0

#     Q_WARN  = True

#     for t in tournament_result:

#         pl_rates = []
#         team_players_id[t["team"]["id"]] = []
#         for pl in t["teamMembers"]:
#             if pl["player"]["id"] not in players_rating:
#             #     players_rating[pl["player"]["id"]] = PLAYER_START_RATING
#                 pl_rates.append(PLAYER_START_RATING)
#             else:
#                 pl_rates.append(players_rating[pl["player"]["id"]])
#             team_players_id[t["team"]["id"]].append(pl["player"]["id"])
        
#         players_num[t["team"]["id"]] = len(pl_rates)

#         if len(pl_rates) == 0:
#             if print_issues:
#                 print("Team", t["team"]["id"], "has no players")
#             player_based_team_ratings[t["team"]["id"]] = None
#             issues.append((t["team"]["id"], "No players data"))
#             continue

#         if len(pl_rates) > 6:
#             player_based_team_ratings[t["team"]["id"]] = independed_ELO(sorted(pl_rates)[-6:], INDEPNDENT_SKILL_QUESTION)
#         else:
#             player_based_team_ratings[t["team"]["id"]] = independed_ELO(pl_rates, INDEPNDENT_SKILL_QUESTION)


#         qid = 0
#         if not t["team"]["id"] in team_gets:
#             team_gets[t["team"]["id"]] = 0

#         if individual_questions:
#             if t["mask"] is None:
#                 issues.append((t["team"]["id"], "No individual question data"))
#                 if Q_WARN:
#                     if print_issues:
#                         print("WARNING: No question data")#: " + str(t))
#                     Q_WARN = False
#                 team_gets[t["team"]["id"]] = None
#                 # continue
#             else:
#                 for q in t["mask"]:
#                     if not qid in question_gets:
#                         question_gets[qid] = 0
#                     if q == "1":
#                         question_gets[qid] += 1
#                         team_gets[t["team"]["id"]] += 1
#                     qid += 1
#         else:
#             if not "questionsTotal" in t:
#                 issues.append((t["team"]["id"], "No question data"))
#                 team_gets[t["team"]["id"]] = None
#             elif t["questionsTotal"] is None:
#                 team_gets[t["team"]["id"]] = None
#                 issues.append((t["team"]["id"], "No question data"))
#             elif t["questionsTotal"] == 0:
#                 if not "position" in t:
#                     team_gets[t["team"]["id"]] = None
#                     issues.append((t["team"]["id"], "No question data"))
#                 if t["position"] == 9999:
#                     team_gets[t["team"]["id"]] = None
#                     issues.append((t["team"]["id"], "No question data"))
#             else:
#                 team_gets[t["team"]["id"]] = t["questionsTotal"]
#                 total_gets += t["questionsTotal"]

#         # if not t["team"]["id"] in teams_ratings:
#         #     teams_ratings[t["team"]["id"]] = TEAM_START_RATING
        

#         places.append(t["position"])
        
#         if not team_gets[t["team"]["id"]] is None:
#             local_teams_rates.append(player_based_team_ratings[t["team"]["id"]])
#         if max_qid < qid:
#             max_qid = qid


#     score = {}

#     if detailed_print:
#         print("Data preparation: " + str(datetime.now() - start_time))
    
#     if individual_questions:
#         total_gets = sum([question_gets[x] for x in question_gets])
#         question_number = len(question_gets)
#         Q_hardnes = max_like(1000, local_teams_rates, total_gets/question_number, False)
    
#         for q in range(max_qid):
#             question_values.append(max_like(1000, local_teams_rates, question_gets[q], False))
#     else:
#         qval = max_like(1000, local_teams_rates, total_gets/question_number, False)
#         question_values = [qval]*question_number
#         Q_hardnes = qval

    
#     team_delta = {}
#     player_delta = {}

#     # print(team_gets, team_players_id)

#     for tm in player_based_team_ratings:
#         if player_based_team_ratings[tm] is None:
#             continue
#         if team_gets[tm] is None:
#             team_delta[tm] = None    
#         else:
#             team_delta[tm] = (team_gets[tm] - ELO_estimate(player_based_team_ratings[tm], question_values)) * tournament_weight
#             w = 1.
#             if players_num[tm] > 6:
#                 w = w*6 /players_num[tm]
            
#             for pl in team_players_id[tm]:
#                 if tournament_weight > NON_RATE_DELTA_MULTIPLIER:
#                     if pl in players_rated_games_cnt:
#                         if players_rated_games_cnt[pl] < 10:
#                             wl = w*10/tournament_weight
#                         elif players_rated_games_cnt[pl] < 20:
#                             wl = w*7/tournament_weight
#                         elif players_rated_games_cnt[pl] < 30:
#                             wl = w*5/tournament_weight
#                         else:
#                             wl = w*3/tournament_weight

#                     else:
#                         wl = w*10/tournament_weight
#                 else:
#                     wl = w
                
#                 player_delta[pl] = team_delta[tm] * wl

#     # print("t", team_delta, player_delta)

#     if detailed_print:
#         print("Totaly: " + str(datetime.now() - start_time))
    
#     return (player_based_team_ratings, question_values, player_delta, score, Q_hardnes, issues)

def season_to_date_string(seasone_num, for_comparison = False):
    season_dt = date.fromisoformat("2021-09-02") + timedelta(days=7*seasone_num+int(for_comparison))
    return season_dt.strftime("%Y-%m-%d")


def season_by_datestring(datestring) -> int:
    '''Return season/release id for date. Release 0 boundary is 2021-09-02 23:59:59'''
    return math.ceil((datetime.fromisoformat(datestring).date() - date.fromisoformat("2021-09-03")).days/7)

def season_by_datetime(date_value) -> int:
    '''Return season/release id for date. Release 0 boundary is 2021-09-02 23:59:59'''
    return math.ceil((date_value.date() - date.fromisoformat("2021-09-03")).days/7)

def finalize_release(conn, release, player_rates, player_counts):
    # conn = sqlite3.connect(r'Output/rating.db')
    release_deltas = conn.execute(f"SELECT playerid, SUM(deltarating), SUM(rated) FROM playerratingsdelta WHERE (releaseid = {release}) and (deltarating IS NOT NULL) GROUP BY playerid")
    prev_release_new_players = []
    rates_with_places = []

    #TODO: add potecial rating degradation
    for pid in player_rates:
        player_rates[pid] -= RATING_WEEK_DEGRADATION*(player_rates[pid] - PLAYER_START_RATING)

    for plr in release_deltas:
        if plr[0] in player_rates:
            player_rates[plr[0]] += plr[1]
        else:
            player_rates[plr[0]] = PLAYER_START_RATING + plr[1]
            prev_release_new_players.append((release-1, plr[0], PLAYER_START_RATING))
            # player_counts[plr[0]] = plr[2]

        if plr[0] in player_counts:
            player_counts[plr[0]] += plr[2]
        else:
            player_counts[plr[0]] = plr[2]


    places = rankdata([-player_rates[pid] for pid in player_rates])    
    for place, pid in zip(places, player_rates):
        rates_with_places.append((release, pid, player_rates[pid], place))
    
    conn.executemany("INSERT INTO playerratings(releaseid, playerid, playerrating) VALUES(?,?,?)", prev_release_new_players)
    conn.executemany("INSERT INTO playerratings(releaseid, playerid, playerrating, place) VALUES(?,?,?,?)", rates_with_places)
    conn.commit()

    update_team_ratings(conn, release)

    # conn.close()
    
        



    

# @profile
def process_all_data(rating_db, data_db, start_from_release = 1):
    
    team_rates = {}
    player_ratings = {}
    players_rated_games_cnt = {}
   
    save_data = True

    DBconn = sqlite3.connect(rating_db)
    DBconn.execute("ATTACH DATABASE ? AS data;", (data_db,))
 
    cursor = DBconn.cursor()
    # cursor.execute("ATTACH DATABASE ? AS data;", (data_db,))
    
    if start_from_release > 1:
        players_rates = cursor.execute(f"SELECT playerid, playerrating FROM playerratings WHERE releaseid = {start_from_release-1}").fetchall()
        player_ratings = {x[0]:x[1] for x in players_rates}
        players_rated = cursor.execute(f"SELECT playerid, SUM(maii_rating) FROM playerratingsdelta JOIN data.tournaments as tournaments ON playerratingsdelta.tournamentid=tournaments.tournamentid WHERE tournaments.dateEnd < '{season_to_date_string(start_from_release-1,  True)}' and maii_rating=1 GROUP BY playerid").fetchall()
        players_rated_games_cnt = {x[0]:x[1] for x in players_rated}
    
    all_issues = []

    print("reading tournaments_info")
    
    # tournaments_info_list = connector.get_all_rated_tournaments()
 
    # with open('tournaments_info.json', 'r', encoding="utf8") as JSON:
    #     tournament_info_dict = json.load(JSON)


    minimal_end_date = season_to_date_string(start_from_release-1, True)
    actual_release = season_by_datetime(datetime.now())
    max_end_data = season_to_date_string(actual_release + 2, True)

    ordered_tournament_ids = cursor.execute("SELECT tournamentid, dateEnd, maii_rating, questionQty, fulljson FROM data.tournaments WHERE dateEnd < ? AND dateEnd > ? and typeoft_id <> 5 ORDER BY dateEnd", (max_end_data, minimal_end_date)).fetchall()

    print("tornaments to process", len(ordered_tournament_ids))

    # ordered_tournament_ids = [t for t in tournament_info_dict if (tournament_info_dict[t]["dateEnd"] < max_end_data) and (tournament_info_dict[t]["dateEnd"] >= minimal_end_date)and(tournament_info_dict[t]["type"]["id"] != 5)]
    # ordered_tournament_ids.sort(key = lambda x: tournament_info_dict[x]["dateEnd"])
    # results = {}
    # release_results = {start_from_release-1:{}, start_from_release:{}}
    # release_results[start_from_release-1]["player_ratings"] = deepcopy(player_ratings)

    cnt = 0

    # release_date = datetime(year = 2013, month = 9, day = 5) 
    release_date = datetime(year = 2021, month = 9, day = 3) + timedelta(days=7*(start_from_release)) 
    release_num = start_from_release
    tournaments_by_reliases = [[]]
  
    # print(ordered_tournament_ids)

    for t in tqdm(ordered_tournament_ids):

        start = datetime.now()
        print("Process tournament "+str(t[0])+ " start at "+str(start))
    
        while not t[1] < str(release_date):

            finalize_release(DBconn, release_num, player_ratings, player_counts=players_rated_games_cnt)
                        
            records = []
            
            tournaments_by_reliases.append([])
            release_num += 1
            release_date += timedelta(days = 7)

            print("Start working on release "+str(release_num)+":  "+str(release_date))
            logger.debug("Start working on release "+str(release_num)+":  "+str(release_date))

        questionQty = 0
        # print(tournament_info_dict[t]["questionQty"])
        QQuantity = {}
        if t[3]:
            if json.loads(t[3]):
                QQuantity = json.loads(t[3])
        
        for qqt in QQuantity:
            questionQty += QQuantity[qqt]

        if t[2]:                                                        #"maiiRating"
            tournament_weight = DELTA_MULTIPLIER
            rated = 1
        else:
            tournament_weight = NON_RATE_DELTA_MULTIPLIER
            rated = 0

        # if tournament_info_dict[t]["type"]["id"] in [2, 3, 6, 8, 4]:
        #     if not "questionQty" in tournament_info_dict[t]:
        #         tournament_weight = NON_RATE_DELTA_MULTIPLIER
        #         rated = 0
        #     else:
        #         tq = sum(tournament_info_dict[t]["questionQty"][qq] for qq in tournament_info_dict[t]["questionQty"])
        #         if tq > 150:
        #             tournament_weight = NON_RATE_DELTA_MULTIPLIER
        #             rated = 0
        #         else:
        #             tournament_weight = DELTA_MULTIPLIER
        #             rated = 1
                        
        # else:
        #     tournament_weight = NON_RATE_DELTA_MULTIPLIER
        #     rated = 0
    
 
        delta, qv, delta_pl, score, Q_hardnes, issues = process_one_tournament_from_DB(DBconn, t[0], player_ratings, True, questionQty, tournament_weight, players_rated_games_cnt)

        all_issues += [(t[0], a, b) for a, b in issues]

        if save_data:
            qvalues = [(t[0], i+1, qvl) for (i,qvl) in enumerate(qv)]
            tournamentrating_data = []
            players_delta_rows = []
            legs_data = []
            # team_places = sorted([x for x in delta], key = lambda x: -delta[x])
            
            team_results = DBconn.execute(f"SELECT teamid, totalquestions, mask, place FROM results WHERE tournamentid =={t[0]}")
            for tm in team_results:
                if tm[0] in delta:
                    if (not delta[tm[0]] is None):
                        atmost, atleast = estimate_p_values(delta[tm[0]], qv, tm[1]) if (not (tm[1] == None)) else (None, None)
                        team_perf = max_like(1000, qv, tm[1]) if (not (tm[1] == None)) else None
                        tournamentrating_data.append((t[0], tm[0], delta[tm[0]], ELO_estimate(delta[tm[0]], qv), atleast, atmost, team_perf))

                    q_last = 0
                    if (not tm[2] is None) and (not delta[tm[0]] is None):
                        for qqt in sorted(QQuantity, key=lambda x: int(x)):
                            leg_N = QQuantity[qqt]
                            q_cur = q_last + leg_N
                            leg_Total = sum([x=="1" for x in tm[2][q_last:q_cur]])
                            atmost, atleast = estimate_p_values(delta[tm[0]], qv[q_last:q_cur], leg_Total)

                            legs_data.append((t[0], tm[0], int(qqt), leg_N, tm[2][q_last:q_cur],leg_Total, ELO_estimate(delta[tm[0]], qv[q_last:q_cur]), atleast, atmost))
                            q_last = q_cur
                            # bytes = f.write(my_t["current"]["name"] + "; " +str(delta[my_t["team"]["id"]])+ "; " +str(len(my_t["teamMembers"])) +"; "+ str(my_t["position"]) + "; " + str(team_places.index(my_t["team"]["id"])+1)+"; " + str(my_t["questionsTotal"]) + "; " + str(ELO_estimate(delta[my_t["team"]["id"]], qv))+"\n")
            
            pl_results = DBconn.execute(f"SELECT playerid, teamid FROM roster WHERE tournamentid =={t[0]}")
            for pl in pl_results:
                if pl[0] in delta_pl:
                    players_delta_rows.append((release_num, pl[0], delta_pl[pl[0]], t[0], pl[1], rated))
                else:
                    players_delta_rows.append((release_num, pl[0], None, t[0], pl[1], rated))

   
                        


            # else:        
            #     for my_t in data:
            #         if my_t["team"]["id"] in delta:
            #             if (not delta[my_t["team"]["id"]] is None):
            #         # if ((not (my_t["mask"] == None)) |  (not (my_t["questionsTotal"] == None))) and (not delta[my_t["team"]["id"]] is None):
            #             # if my_t["team"]["id"] in delta:
            #                 atmost, atleast = estimate_p_values(delta[my_t["team"]["id"]], qv, my_t["questionsTotal"]) if (not (my_t["questionsTotal"] == None)) else (None, None)
            #                 team_perf = max_like(1000, qv, my_t["questionsTotal"]) if (not (my_t["questionsTotal"] == None)) else None
            #                 tournamentrating_data.append((t, my_t["team"]["id"], delta[my_t["team"]["id"]], ELO_estimate(delta[my_t["team"]["id"]], qv), atleast, atmost, team_perf))
            #                 for pld in my_t["teamMembers"]:
            #                     roster_data.append((t, pld["player"]["id"], my_t["team"]["id"]))
            #                     if pld["player"]["id"] in delta_pl:
            #                         players_delta_rows.append((release_num, pld["player"]["id"], delta_pl[pld["player"]["id"]], t, my_t["team"]["id"],rated))
            #                     else:
            #                         players_delta_rows.append((release_num, pld["player"]["id"], None, t, my_t["team"]["id"],rated))

            #                 # q_diff.append(abs(my_t["questionsTotal"] - ELO_estimate(delta[my_t["team"]["id"]], qv)))
            #                 # q2_diff.append((my_t["questionsTotal"] - ELO_estimate(delta[my_t["team"]["id"]], qv))**2)
            #             q_last = 0
                        
            #             if (not my_t["mask"] is None) and (not delta[my_t["team"]["id"]] is None):
            #                 for qqt in sorted(tournament_info_dict[t]["questionQty"], key=lambda x: int(x)):
            #                     leg_N = tournament_info_dict[t]["questionQty"][qqt]
            #                     q_cur = q_last + leg_N
            #                     leg_Total = sum([x=="1" for x in  my_t["mask"][q_last:q_cur]])
            #                     atmost, atleast = estimate_p_values(delta[my_t["team"]["id"]], qv[q_last:q_cur], leg_Total)

            #                     legs_data.append((t, my_t["team"]["id"], int(qqt), leg_N, my_t["mask"][q_last:q_cur],leg_Total, ELO_estimate(delta[my_t["team"]["id"]], qv[q_last:q_cur]), atleast, atmost))
            #                     q_last = q_cur
            #                     # bytes = f.write(my_t["current"]["name"] + "; " +str(delta[my_t["team"]["id"]])+ "; " +str(len(my_t["teamMembers"])) +"; "+ str(my_t["position"]) + "; " + str(team_places.index(my_t["team"]["id"])+1)+"; " + str(my_t["questionsTotal"]) + "; " + str(ELO_estimate(delta[my_t["team"]["id"]], qv))+"\n")
            
        cursor.executemany('INSERT INTO questionrating VALUES(?,?,?);', qvalues)            
        cursor.executemany('INSERT INTO tournamentratings VALUES(?,?,?,?,?,?,?);', tournamentrating_data)    
        cursor.executemany('INSERT INTO tournaments_legs VALUES(?,?,?,?,?,?,?,?,?);', legs_data)        
        cursor.executemany('INSERT INTO playerratingsdelta VALUES(?,?,?,?,?,?);', players_delta_rows)    

        # if not from_DB:
        #     cursor.executemany('INSERT INTO roster VALUES(?,?,?);',roster_data)        
        #     cursor.executemany('INSERT INTO results VALUES(?,?,?,?,?,?);',results_data)        
        
        # print(tournament_info_dict[t])

        cursor.execute("INSERT OR REPLACE INTO tournamentshardnes VALUES(?,?);", (t[0], Q_hardnes))

        DBconn.commit()
        # results[t] = {}
        # results[t]["qv"] = qv
        # results[t]["delta_players"] = delta_pl
        # results[t]["team_rates"] = delta

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
    
    # records = []
    # for tid in tournaments_by_reliases[-1]:
    #     for pid in results[tid]["delta_players"]:
    #         player_ratings[pid] += results[tid]["delta_players"][pid]
    #         records.append((release_num, pid, results[tid]["delta_players"][pid], tid))

    # #insert multiple records in a single query
    # # cursor.executemany('INSERT INTO playerratingsdelta VALUES(?,?,?,?);',records)    

    # release_results[release_num]["player_ratings"] = deepcopy(player_ratings)
    
    # records = []
    # for place, pid in enumerate(sorted(player_ratings, key=lambda x: -player_ratings[x])):
    #     records.append((release_num, pid, player_ratings[pid], place+1))
    #     if not pid in release_results[release_num-1]["player_ratings"]:
    #         records.append((release_num-1, pid, PLAYER_START_RATING, None))


    # cursor.executemany('INSERT INTO playerratings VALUES(?,?,?,?);',records)
    DBconn.commit()

    finalize_release(DBconn, release_num, player_ratings, player_counts=players_rated_games_cnt)
    DBconn.close()


    
    #Предполагаем, что кэш больше не обновляется, все его изиенения в отдельных процессах/блоках
    #print("Save chach. Be patient")
    
    #connector.save_cache("cache.json")


    with open("issues.json", "w") as file:
        json.dump(all_issues, file)

    
    
def clear_rates(rates_db, data_db, start_from_release = 0):
    #try to clear all data
    conn = sqlite3.connect(rates_db)
    conn.execute("ATTACH DATABASE ? AS data;", (data_db,))


    logging.info("Clear DB:")
    cursor = conn.cursor()
    if start_from_release == 0:
        cursor.execute('DELETE FROM playerratings;')
        cursor.execute('DELETE FROM playerratingsdelta;')
        cursor.execute('DELETE FROM tournamentratings;')
        cursor.execute('DELETE FROM questionrating;')
        cursor.execute('DELETE FROM tournaments_legs;')
    else:

        logging.info("    playerratings")        
        cursor.execute(f'DELETE FROM playerratings WHERE releaseid >= {start_from_release};')
        logging.info("    playerratingsdelta")        
        cursor.execute(f'DELETE FROM playerratingsdelta WHERE releaseid >= {start_from_release};')
        logging.info("    tournamentratings")        
        cursor.execute(f'DELETE FROM tournamentratings WHERE ROWID IN (SELECT tournamentratings.ROWID FROM tournamentratings JOIN data.tournaments as tournaments ON tournamentratings.tournamentid=tournaments.tournamentid WHERE dateEnd >= "{season_to_date_string(start_from_release-1, True)}");')
        logging.info("    questionrating")        
        cursor.execute(f'DELETE FROM questionrating WHERE ROWID IN (SELECT questionrating.ROWID FROM questionrating JOIN data.tournaments as tournaments ON questionrating.tournamentid=tournaments.tournamentid WHERE dateEnd >= "{season_to_date_string(start_from_release-1, True)}");')
        logging.info("    tournaments_legs")        
        cursor.execute(f'DELETE FROM tournaments_legs WHERE ROWID IN (SELECT tournaments_legs.ROWID FROM tournaments_legs JOIN data.tournaments as tournaments ON tournaments_legs.tournamentid=tournaments.tournamentid WHERE dateEnd >= "{season_to_date_string(start_from_release-1, True)}");')

    conn.commit()
    conn.close()

def update_tournaments_db(data_db):
    logging.info("Start tournament update")
    connector = ChGK_API_connector(False)
    print(data_db)
    
    conn = sqlite3.connect(data_db)
    # tournaments_info_dict = {}
    
    # if os.path.isfile("tournaments_info.json"):
    #     with open("tournaments_info.json", "r") as file:
    #         tournaments_info_dict = json.load(file)
    
    current_date = str(datetime.now())    

    print(current_date)
    updated = "2021-09-01"

    last_updated = conn.execute("SELECT MAX(lastSynchDate) from tournaments").fetchone()

    if last_updated:
        updated = last_updated[0][:10]

    logger.info(f"Tournament update from {updated}")

    test_new = connector.get_all_tournaments(startdate_after="2021-09-01", last_edit_date=updated) 
    
    for t in tqdm(test_new):
        rs = connector.tournament_results(t["id"], True)
        put_tournament_results_into_DB(t["id"], rs, conn)
        
        if "synchData" in t:
            if "hideQuestionsTo" in t["synchData"]:
                t["hideQuestionsTo"] = t["synchData"]["hideQuestionsTo"]
            else:
               t["hideQuestionsTo"] = t["dateEnd"]
        else:
            t["hideQuestionsTo"] = t["dateEnd"]
        # print()
        # print(t)
        # print()
        # print(f"INSERT OR REPLACE into tournaments (tournamentid, name, startdate, dateEnd, typeoft_id, type, maii_rating, longName, lastSynchDate, hideQuestionsTo, fulljson) VALUES " + 
                            # f'({t["id"]},"{t["name"]}","{t["dateStart"]}", "{t["dateEnd"]}", {t["type"]["id"]}, "{t["type"]["name"]}", {t["maiiRating"]}, "{t["longName"]}", "{current_date}", "{t["synchData"]["hideQuestionsTo"]}", "{json.dumps(t)}")')
        
        conn.execute(f"INSERT OR REPLACE into tournaments (tournamentid, name, dateStart, dateEnd, typeoft_id, type, maii_rating, longName, lastSynchDate, hideQuestionsTo, questionQty, fulljson) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                           (t["id"], t["name"], t["dateStart"], t["dateEnd"], t["type"]["id"], t["type"]["name"], t["maiiRating"], t["longName"], current_date, t["hideQuestionsTo"], None if not "questionQty" in t else json.dumps(t["questionQty"]), json.dumps(t)))
        
     
    to_refresh = conn.execute("SELECT tournamentid, name, dateEnd from tournaments where hideQuestionsTo > lastSynchDate and hideQuestionsTo < ?", (current_date,))
    
    for t in to_refresh:
        logger.debug(f"Unhide tournament {t[0]}")
        rs = connector.tournament_results(t[0], True)
        put_tournament_results_into_DB(t[0], rs, conn)
        test_new.append({"id":t[0], "name": t[1], "dateEnd":t[2]})
        conn.execute(f"UPDATE tournaments SET lastSynchDate = ? WHERE tournamentid = ?", (current_date, t[0]))
    
    
    ordered_changes = sorted([(x["id"], x["name"], x["dateEnd"]) for x in test_new], key=lambda x: x[2])  
    if len(ordered_changes) > 0:
        logger.info(f"Earliest updated tournament {ordered_changes[0]}")
        datestr = ordered_changes[0][2]
        earliest_release = season_by_datestring(datestr)
    else:
        earliest_release = season_by_datetime(datetime.now())

    # connector.save_cache("cache.pickle", to_pickle=True)
    # with open("tournaments_info.json", "w") as file:
    #     json.dump(tournaments_info_dict, file)
    logging.info("Tournament update finished")
    conn.close()
    return(earliest_release)

def update_team_ratings(conn, actual_release = 0):
    # conn = sqlite3.connect(r'Output/rating.db')
    # conn = sqlite3.connect(rating_db)
    # conn.execute("ATTACH DATABASE ? AS data;", (data_db,))
    
    my_rost_value = conn.execute(f"SELECT base_roster.teamid as teamid, base_roster.player_id, playerratings.playerrating FROM data.base_roster as base_roster INNER JOIN playerratings ON base_roster.player_id = playerratings.playerid AND playerratings.releaseid = {actual_release} AND base_roster.releaseid = {actual_release} ORDER BY teamid").fetchall()
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

    places = rankdata([-x[1] for x in all_rates]) 
    rates_with_places = []   
    for place, x in zip(places, all_rates):
        rates_with_places.append((actual_release, x[0], x[1], place))

        
    # conn.executescript('DELETE FROM base_team_rates')
    conn.execute('DELETE FROM teambaseratings WHERE releaseid = ?', (actual_release,))
    # conn.executescript('CREATE TABLE base_team_rates (teamid integer primary key, team_rating real, place real);')
    conn.executemany('INSERT INTO teambaseratings VALUES(?,?,?,?);',rates_with_places)
    conn.commit()
    # conn.close()

def set_constants(config):
    global MIN_QUESTION_RATING
    global MAX_QUESTION_RATING
    global DELTA_MULTIPLIER
    global NON_RATE_DELTA_MULTIPLIER
    global INDEPNDENT_SKILL_QUESTION
    global PLAYER_START_RATING
    global TEAM_START_RATING
    global ELO_BASE
    global ELO_NORM
    global RATING_WEEK_DEGRADATION

    MIN_QUESTION_RATING = config["RATING_SETTINGS"].getfloat("MIN_QUESTION_RATING")
    MAX_QUESTION_RATING = config["RATING_SETTINGS"].getfloat("MAX_QUESTION_RATING")
    DELTA_MULTIPLIER = config["RATING_SETTINGS"].getfloat("DELTA_MULTIPLIER")
    NON_RATE_DELTA_MULTIPLIER = config["RATING_SETTINGS"].getfloat("NON_RATE_DELTA_MULTIPLIER")
    INDEPNDENT_SKILL_QUESTION = config["RATING_SETTINGS"].getfloat("INDEPNDENT_SKILL_QUESTION")
    PLAYER_START_RATING = config["RATING_SETTINGS"].getfloat("PLAYER_START_RATING")
    TEAM_START_RATING = config["RATING_SETTINGS"].getfloat("TEAM_START_RATING")
    ELO_BASE = config["RATING_SETTINGS"].getfloat("ELO_BASE")
    ELO_NORM = config["RATING_SETTINGS"].getfloat("ELO_NORM")
    RATING_WEEK_DEGRADATION = config["RATING_SETTINGS"].getfloat("RATING_WEEK_DEGRADATION")


# @profile
def main():

    if len(sys.argv) <= 1:
        print("Use command 'python rating.py config.ini'")
        param_fname = "config.ini"
    else:
        param_fname = sys.argv[1]

    print(param_fname)
    config = configparser.ConfigParser()
    config.read(param_fname)    
    
    data_db = config['DATABASES']['data_db']
    rating_db = config['DATABASES']['ratings_db']
    
    set_constants(config)   
    
    FORMAT = '%(asctime)s %(message)s'
    logging.basicConfig(level=logging.DEBUG, format = FORMAT, filename="rating.log")
    logging.info("Start rating estimation")

    actual_release = season_by_datetime(datetime.now())

    start_from_release = update_tournaments_db(data_db)
    
    # start_from_release = 0
    # print(rating_db)

    clear_rates(rating_db, data_db, start_from_release = start_from_release)
    
    process_all_data(rating_db, data_db, start_from_release = start_from_release)
    # update_team_ratings(rating_db, data_db, actual_release)

    exit(0)

    import shutil

    logging.info("base copy start")
    try:
        shutil.copyfile('Output/rating.db', 'Output/rating_for_site_copy.db')
    except Exception:
        shutil.copyfile('Output/rating.db', 'Output/rating_for_site_copy.db')
    logging.info("base copy finished")
    logging.info("start move")

    if os.path.isfile("Output/rating_for_site_copy.db"):
        try:
            shutil.move("Output/rating_for_site_copy.db", "Output/rating_for_site.db")
        except Exception:
            pass
        
    logging.info("move finished")
    

if __name__ == "__main__":
    main()