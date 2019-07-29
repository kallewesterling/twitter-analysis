# This is a package for quick Twitter analysis based on a Twitter username
import tweepy, json, pickle, gzip
from pathlib import Path
from datetime import datetime as dt

# for debug
from pprint import pprint

# setup
cache_folder = "./__twitteranalysis-cache__/"
twitter_settings = {
    "wait_on_rate_limit": True,
    "wait_on_rate_limit_notify": True,
}





cache = {
    "parent": Path(cache_folder),
    "tweets": Path(cache_folder) / "tweets",
    "users": Path(cache_folder) / "users",
    "lists": Path(cache_folder) / "lists",
    "snapshots": Path(cache_folder) / "snapshots"
}


class twitteranalysis():
    def __init__(self, username=None, consumer_key=None, consumer_secret=None, access_token=None, access_token_secret=None):
        if username is None: raise SyntaxError("This module needs a username to run.")
        if consumer_key is None or consumer_secret is None or access_token is None or access_token_secret is None: raise SyntaxError("This module needs all four of Twitter's API's security measures to run: \nPass in a consumer_key, consumer_secret, access_token, and access_token_secret when creating a new instance.")

        _check_cache_folder()
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)

        self.username = username

        self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)
        self.friends_dict, self.followers_dict, self.fans_dict, self.stans_dict = None, None, None, None

    def __str__(self):
        return(f"Initialized with username {self.username}.")

    def _friends(self, provide="dict", force=False):
        ''' Provides a list of "friends," people who the user follows. '''
        if provide not in ["dict", "screen_name", "id"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self.friends_dict is None or force is True: self.friends_dict = self._get_cached_users(provide="friends", force=force)
        if provide is "dict": return(self.friends_dict)
        if provide is "screen_name": return(list(self.friends_dict.values()))
        if provide is "id": return(list(self.friends_dict.keys()))

    def _followers(self, provide="dict", force=False):
        ''' Provides a list of "followers," people who follow the user. '''
        if provide not in ["dict", "screen_name", "id"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self.followers_dict is None or force is True: self.followers_dict = self._get_cached_users(provide="followers", force=force)
        if provide is "dict": return(self.followers_dict)
        if provide is "screen_name": return(list(self.followers_dict.values()))
        if provide is "id": return(list(self.followers_dict.keys()))

    def _fans(self, provide="dict", force=False):
        ''' Provides a list of "fans," people who follow the user but the user does not follow back. '''
        if provide not in ["dict", "screen_name", "id"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self.fans_dict is None or force is True: self.fans_dict = self._get_cached_users(provide="fans", force=force)
        if provide is "dict": return(self.fans_dict)
        if provide is "screen_name": return(list(self.fans_dict.values()))
        if provide is "id": return(list(self.fans_dict.keys()))

    def _stans(self, provide="dict", force=False):
        ''' Provides a list of "stans," people the user follows who do not follow the user. '''
        if provide not in ["dict", "screen_name", "id"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self.stans_dict is None or force is True: self.stans_dict = self._get_cached_users(provide="stans", force=force)
        if provide is "dict": return(self.stans_dict)
        if provide is "screen_name": return(list(self.stans_dict.values()))
        if provide is "id": return(list(self.stans_dict.keys()))

    @property
    def friends(self):
        return(self._friends())

    @property
    def followers(self):
        return(self._followers())

    @property
    def fans(self):
        return(self._fans())

    @property
    def stans(self):
        return(self._stans())

    def _id_list_to_username(self, _list, force=False):
        _newlist = []
        for _id in _list:
            _json = self._get_cached_user(id=_id, force=force)
            if _json['screen_name'] not in _newlist: _newlist.append(_json['screen_name'])
        return(_newlist)

    def take_snapshot(self):
        _ts = int(dt.now().timestamp())
        _ts_dir = cache['snapshots'] / str(_ts)
        snapshot = {
            'username': self.username,
            stans': self._stans(provide="id"),
            'fans': self._fans(provide="id"),
            'friends': self._friends(provide="id"),
            'followers': self._followers(provide="id")
        }
        try:
            with gzip.open(_ts_dir,'wb+') as f:
                pickle.dump(snapshot, f)
            return(_ts_dir)
        except:
            raise RuntimeError("Everything crashed.")


    def _get_cached_tweet(self, id=None):
        _location = cache['tweets'] / str(id)
        if not _location.is_file():
            tweet = self.api.get_status(id)
            _json = tweet._json
            with open(_location, 'w+') as f:
                json.dump(_json, f)
        else:
            with open(_location, 'r') as f:
                try:
                    _json = json.load(f)
                except:
                    raise RuntimeError(f"Could not read JSON file {_location}.")
        return(_json)


    def _get_cached_user(self, id=None, force=False):
        _location = cache['users'] / str(id)
        if not _location.is_file() or force is True:
            tweet = self.api.get_user(id)
            _json = tweet._json
            with open(_location, 'w+') as f:
                json.dump(_json, f)
        else:
            with open(_location, 'r') as f:
                try:
                    _json = json.load(f)
                except:
                    raise RuntimeError(f"Could not read JSON file {_location}.")
        return(_json)

    def _get_cached_users(self, provide=None, force=False):
        ''' This internal function makes sure that the cache folder is set up. '''
        _location = cache['lists'] / str(provide)
        if not _location.is_file() or force is True:
            if provide == "friends":
                _list_of_ids = self.api.friends_ids(screen_name=self.username)
            elif provide=="followers":
                _list_of_ids = self.api.followers_ids(screen_name=self.username)
            elif provide=="fans":
                _list_of_ids = set(self.api.followers_ids(screen_name=self.username)) - set(self.api.friends_ids(screen_name=self.username))
            elif provide=="stans":
                _list_of_ids = set(self.api.friends_ids(screen_name=self.username)) - set(self.api.followers_ids(screen_name=self.username))

            _list_of_usernames = self._id_list_to_username(_list_of_ids, force=force)
            _list = dict(zip(_list_of_ids, _list_of_usernames))
            with open(_location, 'w+') as f:
                json.dump(_list, f)
        else:
            with open(_location, 'r') as f:
                try:
                    _list = json.load(f)
                except:
                    raise RuntimeError(f"Could not read JSON file {_location}.")
        return(_list)


def _check_cache_folder():
    ''' This internal function makes sure that the cache folder is set up. '''
    if not cache['tweets'].is_dir():
        try:
            cache['tweets'].mkdir(parents=True)
        except:
            raise RuntimeError(f"Could not create {cache['tweets']}")

    if not cache['users'].is_dir():
            try:
                cache['users'].mkdir(parents=True)
            except:
                raise RuntimeError(f"Could not create {cache['users']}")

    if not cache['lists'].is_dir():
            try:
                cache['lists'].mkdir(parents=True)
            except:
                raise RuntimeError(f"Could not create {cache['lists']}")



def read_snapshot(ts=None):
    ''' Function to read the snapshot of a timestamp passed in as "ts" '''

    if ts is None:
        ''' If no timestamp was passed in, we will go with the most recent snapshot. '''
        newest = None
        for _ in cache['snapshots'].glob("*"):
            if ".DS_Store" not in _.stem: 
                if newest is None: newest = _.stem
                if newest < _.stem: newest = _.stem
        _ts_dir = cache['snapshots'] / Path(newest)
    else:
        _ts_dir = cache['snapshots'] / str(ts)
    try:
        with gzip.open(_ts_dir,'rb') as f:
            snapshot = pickle.load(f)
        snapshot['snapshot-meta'] = {
            'full_path': _ts_dir,
            'filename': _ts_dir.stem,
            'created': dt.fromtimestamp(int(_ts_dir.stem)),
        }
        return(snapshot)
    except:
        raise RuntimeError("Everything crashed.")