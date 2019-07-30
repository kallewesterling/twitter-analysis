# This is a package for quick Twitter analysis based on a Twitter username
import tweepy, json, pickle, gzip, progressbar
from pathlib import Path
from datetime import datetime as dt
import pandas as pd

# for debug
from pprint import pprint

# setup
cache_folder = "./__twitteranalysis-cache__/"
twitter_settings = {
    "wait_on_rate_limit": True,
    "wait_on_rate_limit_notify": True,
}
auto_format = "dict"    # sets the automatic format that your [twitteranalysis-object].followers/friends/stans/fans will return (can be set to "dict", "screen_name", "id", or "df")
force_threshold = {     # files have to be over this many days old when "force=True" forces a download
    "users": 7,
    "tweets": 7,
    "lists": -1,
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

        # Make sure all cache folders are set up correctly
        _check_cache_folder(username=username)

        # Set up variables for the scope of the object
        self.username = username

        # Set up empty variables
        self._friends_dict, self._followers_dict, self._fans_dict, self._stans_dict = None, None, None, None

        # Start the API
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

    def __str__(self):
        return(f"twitteranalysis object starting from username {self.username}.")

    def __repr__(self):
        return(f'twitteranalysis(username="{self.username}")')

    def _friends(self, provide="dict", force=False):
        ''' Provides a list of "friends," people who the user follows. '''
        if provide not in ["dict", "screen_name", "id", "df"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self._friends_dict is None or force is True: self._friends_dict = self._get_cached_list(provide="friends", force=force)
        if provide is "dict": return(self._friends_dict)
        elif provide is "screen_name": return(list(self._friends_dict.values()))
        elif provide is "id": return(list(self._friends_dict.keys()))
        elif provide is "df": return(self._df_from_user_id_list(self._friends_dict.keys()))

    def _followers(self, provide="dict", force=False):
        ''' Provides a list of "followers," people who follow the user. '''
        if provide not in ["dict", "screen_name", "id", "df"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self._followers_dict is None or force is True: self._followers_dict = self._get_cached_list(provide="followers", force=force)
        if provide is "dict": return(self._followers_dict)
        elif provide is "screen_name": return(list(self._followers_dict.values()))
        elif provide is "id": return(list(self._followers_dict.keys()))
        elif provide is "df": return(self._df_from_user_id_list(self._followers_dict.keys()))

    def _fans(self, provide="dict", force=False):
        ''' Provides a list of "fans," people who follow the user but the user does not follow back. '''
        if provide not in ["dict", "screen_name", "id", "df"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self._fans_dict is None or force is True: self._fans_dict = self._get_cached_list(provide="fans", force=force)
        if provide is "dict": return(self._fans_dict)
        elif provide is "screen_name": return(list(self._fans_dict.values()))
        elif provide is "id": return(list(self._fans_dict.keys()))
        elif provide is "df": return(self._df_from_user_id_list(self._fans_dict.keys()))

    def _stans(self, provide="dict", force=False):
        ''' Provides a list of "stans," people the user follows who do not follow the user. '''
        if provide not in ["dict", "screen_name", "id", "df"]: raise RuntimeError('You must provide one of the following as a "provide" parameter: dict, screen_name, or id.')

        if self._stans_dict is None or force is True: self._stans_dict = self._get_cached_list(provide="stans", force=force)
        if provide is "dict": return(self._stans_dict)
        elif provide is "screen_name": return(list(self._stans_dict.values()))
        elif provide is "id": return(list(self._stans_dict.keys()))
        elif provide is "df": return(self._df_from_user_id_list(self._stans_dict.keys()))

    @property
    def friends(self):
        return(self._friends(provide=auto_format))

    @property
    def followers(self):
        return(self._followers(provide=auto_format))

    @property
    def fans(self):
        return(self._fans(provide=auto_format))

    @property
    def stans(self):
        return(self._stans(provide=auto_format))

    def _df_from_user_id_list(self, _id_list, index="screen_name"):
        ''' Returns a pandas DataFrame constructed from a list of Twitter ids by loading the cached JSON file for each user, dropping some specified fields, and then setting an index. '''
        _ = []
        bar = progressbar.ProgressBar(max_value=len(_id_list)).start() # start progressbar
        for i, id in enumerate(_id_list):
            bar.update(i)
            _json = self._get_cached_user(id=str(id))
            for x in ['contributors_enabled', 'default_profile', 'default_profile_image', 'entities', 'following', 'id_str', 'profile_background_color', 'profile_background_image_url', 'profile_background_image_url_https', 'profile_background_tile', 'profile_banner_url', 'profile_image_url', 'profile_image_url_https', 'profile_link_color', 'profile_sidebar_border_color', 'profile_sidebar_fill_color', 'profile_text_color', 'profile_use_background_image']:
                try:
                    del _json[x]
                except:
                    pass  # print(f"Removing {x} didn't work.")
            _.append(_json)
        bar.finish() # finish progressbar
        df = pd.DataFrame.from_dict(_)
        try:
            df.set_index(index, inplace=True)
        except:
            pass # index could not be set but we'll just move ahead!
        return(df)


    def _id_list_to_username(self, _list, force=False):
        ''' Returns a list of usernames from a list of Twitter ids by loading the cached JSON file for each user and adding each screen_name to a new list. '''
        _newlist = []
        bar = progressbar.ProgressBar(max_value=len(_list)).start() # start progressbar
        for i, _id in enumerate(_list):
            bar.update(i)
            _json = self._get_cached_user(id=_id, force=force)
            if _json['screen_name'] not in _newlist: _newlist.append(_json['screen_name'])
        bar.finish() # finish progressbar
        return(_newlist)


    def _get_cached_user(self, id=None, force=False):
        ''' Checks whether the data for a user is already downloaded and if it is not, downloads it and stores it in the cache directory for users. '''
        _location = cache['users'] / str(id)
        if not _location.is_file() or (force is True and days_old(type="users", id=id) >= force_threshold["users"]):
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


    def _get_cached_list(self, provide=None, force=False):
        ''' Provides a list of the cached users for each username. '''
        if provide not in ["friends", "followers", "fans", "stans"]: raise RuntimeError("This function can only provide lists of friends, followers fans, or stans. Set 'provide' parameter accordingly.")

        _location = cache['lists'] / str(provide)
        if not _location.is_file() or (force is True and days_old(type="lists", id=provide) >= force_threshold["lists"]):
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


    def _get_cached_tweet(self, id=None, force=False):
        ''' Checks whether the data for a tweet is already downloaded and if it is not, downloads it and stores it in the cache directory for tweets. '''
        _location = cache['tweets'] / str(id)
        if not _location.is_file() or (force is True and days_old(type="tweets", id=provide) >= force_threshold["tweets"]):
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


    def take_snapshot(self, force=False):
        ''' Takes a snapshot of the current dataset (including followers, friends, fans, and stans) and stores them in the snapshot folder using the current epoch timestamp as filename. The filetype is a gzipped pickle. '''
        current_stans = self._stans(provide="id", force=force)
        current_friends = self._friends(provide="id", force=force)
        current_followers = self._followers(provide="id", force=force)
        current_fans = self._fans(provide="id", force=force)
        print(f"Saving snapshot with {len(current_followers)} followers, {len(current_friends)} friends, {len(current_fans)} fans, and {len(current_stans)} stans.")
        snapshot = {
            'username': self.username,
            'stans': current_stans,
            'fans': current_fans,
            'friends': current_friends,
            'followers': current_followers,
            'stans_count': len(current_stans),
            'fans_count': len(current_fans),
            'friends_count': len(current_friends),
            'followers_count': len(current_followers)
        }
        _ts = int(dt.now().timestamp())
        _ts_dir = cache['snapshots'] / str(_ts)
        try:
            with gzip.open(_ts_dir,'wb+') as f:
                pickle.dump(snapshot, f)
            return(_ts_dir)
        except:
            raise RuntimeError("Everything crashed.")


def _check_cache_folder(username=None):
    ''' Makes sure that the cache folder is correctly set up. '''
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

    if username is not None and (cache['lists'] / str(username)).is_dir() is False:
            try:
                cache['lists'] = cache['lists'] / str(username)
                cache['lists'].mkdir(parents=True)
            except:
                raise RuntimeError(f"Could not create {(cache['lists'] / str(username))}")


def _cleanup_userdata():
    ''' Function to clean up downloaded user data to remove each of their recent tweets. '''
    for _ in cache["u_sers"].glob("*"):
        if _.stem in ['.DS_Store']: continue

        with open(_, "r") as f:         # load in the JSON
            _json = json.load(f)

        try:                            # delete all the recent status information
            del _json['status']
        except:
            pass

        with open(_, "w") as f:         # dump back
            json.dump(_json, f)


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


def diff_snapshot(ts1=None, ts2=None):
    if ts1 is None:
        snapshot1 = read_snapshot()
    else:
        snapshot1 = read_snapshot(ts1)

    snapshot2 = read_snapshot(ts2)
    if snapshot1 == snapshot2:
        return({}) # returns empty dict if no difference
    else:
        return({
            'followers_lost': set(snapshot1['followers']) - set(snapshot2['followers']),
            'followers_gained': set(snapshot2['followers']) - set(snapshot1['followers']),

            'friends_lost': set(snapshot1['friends']) - set(snapshot2['friends']),
            'friends_gained': set(snapshot2['friends']) - set(snapshot1['friends']),

            'fans_lost': set(snapshot1['fans']) - set(snapshot2['fans']),
            'fans_gained': set(snapshot2['fans']) - set(snapshot1['fans']),

            'stans_lost': set(snapshot1['stans']) - set(snapshot2['stans']),
            'stans_gained': set(snapshot2['stans']) - set(snapshot1['stans']),
        })

def age(type="users", id=None, provide="days"):
    """ Returns the age (in days) of a cached file of a certain type and with a certain identifier provided. """

    # Verify all settings
    if type == None: raise SyntaxError('A type must be provided.')
    if id == None: raise SyntaxError('An ID must be provided.')

    path = Path(cache[type] / str(id))
    ctime = path.stat().st_ctime
    if provide=="days": age = (ctime - dt.now().timestamp()) / 3600 / 24
    elif provide=="hours": age = (ctime - dt.now().timestamp()) / 3600
    elif provide=="seconds": age = (ctime - dt.now().timestamp())
    return(round(age, 1))