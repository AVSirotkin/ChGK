#### 
# Usefull functions to communicate with rating.chgk.info though api.rating.chgk.net
# By default we use local cache for basic requests to speed up
####  

#TODO: Handle server response error

BASE_CHGK_API_URL = "https://api.rating.chgk.info"

import json
import pickle as pickle
import requests
import os.path
from datetime import datetime
import time

class ChGK_API_connector:
    
    use_cache = True
    API_cache = {}
    
    def __init__(self, use_cache = True):
        self.use_cache = use_cache
        if use_cache:
            self.API_cache = {"tournament_results":{}, "player_info":{}}
    
    def save_cache(self, file_name, to_pickle = True):
        if to_pickle:
            with open(file_name, "wb") as file:
                pickle.dump(self.API_cache, file)
        else:
            with open(file_name, "w") as file:
                json.dump(self.API_cache, file)

    def load_cache(self, filename, from_pickle = True):
        if not os.path.exists(filename):
            return
        if from_pickle:
            with open(filename, 'rb') as file:
                self.API_cache = pickle.load(file)
        else:
            with open(filename, 'r') as file:
                self.API_cache = json.load(file)

    def get_all_tournaments_id_for_team(self, team_id):
        r = requests.get(BASE_CHGK_API_URL+"/teams/"+str(team_id)+"/tournaments?page=1&itemsPerPage=0&pagination=false", headers={'accept': 'application/json'})
        Tournaments_list = []
        infoA = r.json()
        if infoA["idtournament"] not in Tournaments_list:
            Tournaments_list.append(infoA["idtournament"])
        return Tournaments_list
    
    
    def get_all_tournaments_id_for_player(self, player_id):
        r = requests.get(BASE_CHGK_API_URL+"/players/"+str(player_id)+"/tournaments?page=1&itemsPerPage=0&pagination=false", headers={'accept': 'application/json'})
        Tournaments_list = []
        infoA = r.json()
        for s in infoA:
            if s["idtournament"] not in Tournaments_list:
                Tournaments_list.append(s["idtournament"])
        return Tournaments_list

    def get_all_tournaments_for_player(self, player_id):
        r = requests.get(BASE_CHGK_API_URL+"/players/"+str(player_id)+"/tournaments?page=1&itemsPerPage=0&pagination=false", headers={'accept': 'application/json'})
#        Tournaments_list = []
        infoA = r.json()
        return infoA


    def get_tournament_team_info(self, tournament_id, team_id):
        tr = self.tournament_results(tournament_id)
        for t in tr:
            if str(t["team"]["id"]) == str(team_id):
                return(t["teamMembers"])
        return []


    def get_base_roster_info(self, teamid, season = 58):
        r = requests.get(BASE_CHGK_API_URL+"/teams/"+str(teamid)+"/seasons?page=1&itemsPerPage=500&idseason="+str(season), headers={'accept': 'application/json'})
        infoA = r.json()
        team = []
        for u in infoA:
            if u["dateRemoved"] is None:
                team.append(u["idplayer"])
        return team

        


    def get_all_rated_tournaments(self, page = 1):
        res = []
        next = True
        while next:
            r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page)+"&itemsPerPage=500&properties.maiiRating=true", headers={'accept': 'application/json'})
            infoA = r.json()
            res += infoA
            page += 1
            next = (len(infoA)==500)
        return res
 
    def get_all_tournaments(self, page = 1, startdate_after = "", last_edit_date = ""):
        res = []
        next = True
        if len(startdate_after) > 0:
            suffix = "&dateStart[after]="+startdate_after
        else:
            suffix = ''
        if len(last_edit_date):
            suffix += "&lastEditDate[after]="+last_edit_date

        while next:
            print(datetime.now(), BASE_CHGK_API_URL+"/tournaments?page="+str(page)+"&itemsPerPage=100"+suffix)
            try:
                r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page)+"&itemsPerPage=100"+suffix, headers={'accept': 'application/json'})
            except:
                print("someting BAD!!! We will wait 5 seconds and retry")
                time.sleep(5)
            else:
                if r.status_code == 200:
                    infoA = r.json()
                    res += infoA
                    page += 1
                    next = (len(infoA)==100)
                else:
                    if r.status_code == 500:
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-9)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-8)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-7)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-6)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-5)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-4)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-3)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-2)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10-1)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        r = requests.get(BASE_CHGK_API_URL+"/tournaments?page="+str(page*10)+"&itemsPerPage=20"+suffix, headers={'accept': 'application/json'})
                        infoA = r.json()
                        res += infoA
                        page += 1

                        next = True

                    print(f"bad respose code {r.status_code}")
                    time.sleep(5)

        return res

    def tournament_results(self, idtournament, forced = False, quiet = True, max_attempt = 10):
        if self.use_cache and not forced:
            if str(idtournament) in self.API_cache["tournament_results"]:
                return self.API_cache["tournament_results"][str(idtournament)]
        # if not quiet:
        retry = max_attempt
        results = []
        while retry:
            retry -= 1
            try:
                r = requests.get(BASE_CHGK_API_URL + "/tournaments/"+str(idtournament)+"/results?includeTeamMembers=1&includeMasksAndControversials=1&includeTeamFlags=1&includeRatingB=1", headers={'accept': 'application/json'})
            except:
                print("retry attempt in 5 seconds")
                time.sleep(5)
            else:
                if r.status_code == 200:
                    results = r.json()
                    retry = 0
                else:
                    print(f"retry attempt in 5 seconds due bad response code {r.status_code}")
                    time.sleep(5)


        if self.use_cache:
            self.API_cache["tournament_results"][str(idtournament)] = results
        
        return results
    
    def player_info(self, idplayer, forced = False):
        if self.use_cache and not forced:
            if str(idplayer) in self.API_cache["player_info"]:
                return self.API_cache["player_info"][str(idplayer)]
        results = requests.get(BASE_CHGK_API_URL+"/players/"+str(idplayer), headers={'accept': 'application/json'}
).json()
        if self.use_cache:
            self.API_cache["player_info"][str(idplayer)] = results
        return results

    def get_venue_info(self, venueid):
        results = requests.get(BASE_CHGK_API_URL+"/venues/"+str(venueid), headers={'accept': 'application/json'}
).json()
        return results

  
