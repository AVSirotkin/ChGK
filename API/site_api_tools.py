#### 
# Usefull functions to communicate with rating.chgk.info though api.rating.chgk.net
# By default we use local cache for basic requests to speed up
####  

#TODO: Handle server response error

BASE_CHGK_API_URL = "https://api.rating.chgk.net"

import json
import requests
import os.path

class ChGK_API_connector:
    
    use_cache = True
    API_cache = {}
    
    def __init__(self, use_cache = True):
        self.use_cache = use_cache
        if use_cache:
            self.API_cache = {"tournament_results":{}, "player_info":{}}
    
    def save_cache(self, file_name):
        with open(file_name, "w") as file:
            json.dump(self.API_cache, file)

    def load_cache(self, filename):
        if not os.path.exists(filename):
            return
        with open(filename, 'r') as JSON:
            self.API_cache = json.load(JSON)

    def get_all_tournaments_id_for_team(self, team_id):
        r = requests.get(BASE_CHGK_API_URL+"/teams/"+str(team_id)+"/tournaments?page=1&itemsPerPage=0&pagination=false")
        Tournaments_list = []
        infoA = r.json()
        for s in infoA['hydra:member']:
            if s["idtournament"] not in Tournaments_list:
                Tournaments_list.append(s["idtournament"])
        return Tournaments_list
    
    def tournament_results(self, idtournament, forced = False):
        if self.use_cache and not forced:
            if str(idtournament) in self.API_cache["tournament_results"]:
                return self.API_cache["tournament_results"][str(idtournament)]
        results = requests.get("https://api.rating.chgk.net/tournaments/"+str(idtournament)+"/results?includeTeamMembers=1&includeMasksAndControversials=1&includeTeamFlags=0&includeRatingB=1", headers={'accept': 'application/json'}
).json()
        if self.use_cache:
            self.API_cache["tournament_results"][str(idtournament)] = results
        return results
    
    def player_info(self, idplayer, forced = False):
        if self.use_cache and not forced:
            if str(idplayer) in self.API_cache["player_info"]:
                return self.API_cache["player_info"][str(idplayer)]
        results = requests.get("https://api.rating.chgk.net/players/"+str(idplayer), headers={'accept': 'application/json'}
).json()
        if self.use_cache:
            self.API_cache["player_info"][str(idplayer)] = results
        return results


  
