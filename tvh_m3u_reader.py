'''
Created on 11.03.2013

@author: scond_000
inspi by https://github.com/Glandos/m3u_to_tv
'''
import argparse
import urllib2
import urllib
import json

url_prefix = set(('http', 'rtp', 'udp'))


def send_update(url, json_object):
    try:
        data = {'op': 'update', 'entries': '%s' % json.dumps(json_object, ensure_ascii=False).encode("utf-8")}
        response = urllib2.urlopen(url, urllib.urlencode(data))
        return True
    except:
        print 'Error while sending update for %s' % json.dumps(json_object, ensure_ascii=False)
        return False


def create_iptv_service(tvh_url):
    try:
        response = urllib2.urlopen(tvh_url + "/iptv/services", "op=create")
        service = json.load(response)
        return service
    except:
        print 'Error while creating IPTV service'
        return False


def get_iptv_service(tvh_url):
    try:
        response = urllib2.urlopen(tvh_url + "/iptv/services", "op=get")
        service = json.load(response)['entries']
        return service
    except:
        print 'Error while creating IPTV service'
        return False


def find_service(items, name):
    for item in items:
        if item['channelname'] == name:
            return item['id']


def parse_channels(playlist, follow_links=False):
    try:
        pls_file = open(playlist)
    except IOError:
        pls_file = urllib2.urlopen(playlist)

    channels = {}
    for line in pls_file:
        line = line.strip()
        if line.startswith('#EXTINF'):
            _, _, name = line.partition(',')
            name = name.decode("utf-8")
        else:
            prefix, _, link = line.partition('://')
            if prefix in url_prefix:
                if line.endswith('m3u'):
                    if follow_links:
                        channels.update(parse_channels(line, True))
                else:
                    if link[0] == '@':
                        link = link[1:]
                    ip, _, port = link.partition(':')
                    channels[name] = (ip, port)

    return channels


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Read a playlist and feed it to TVHeadend')
    parser.add_argument('--playlist-url', '-l')
    parser.add_argument('--follow_links', action='store_true')
    parser.add_argument('--tvheadend', '-tvh')
    parser.add_argument('--user', '-u')
    parser.add_argument('--password', '-p')
    args = parser.parse_args()

    auth_handler = urllib2.HTTPBasicAuthHandler()
    auth_handler.add_password(realm='tvheadend',
                      uri=args.tvheadend,#'http://192.168.175.9:9981/',
                      user=args.user,
                      passwd=args.password)
    opener = urllib2.build_opener(auth_handler)
    # ...and install it globally so it can be used with urlopen.
    urllib2.install_opener(opener)

    chans = parse_channels(args.playlist_url, args.follow_links)
    ichans = {}
    pre_chans = get_iptv_service(args.tvheadend)
    for cname, clink in chans.items():
        cid = find_service(pre_chans, cname)
        if not cid:
            cid = create_iptv_service(args.tvheadend)['id']
        ichans[cid] = (cname, clink[0], clink[1])

    updates = []
    for cid, chan in ichans.iteritems():
        update = {'id': cid,  # Yes, it is different
                  'channelname': chan[0],
                  'group': chan[1],
                  'port':  chan[2],
                  'interface': 'eth0'}
        updates.append(update)
    send_update(args.tvheadend + "/iptv/services", updates)
