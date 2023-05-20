#!/usr/bin/python3
#      author: mind2hex
# description: simple web directory enumeration tool

import argparse 
import requests
from time import sleep
from sys import argv
from urllib.parse import quote
from random import choice as random_choice
from django.core.validators import URLValidator
from alive_progress import alive_bar
from chardet import detect as detect_encoding
from inspect import currentframe
from bs4 import BeautifulSoup
from urllib.parse import urlparse


def banner():
    author="mind2hex"
    version="1.0"
    print(f"""
               _      _____                    _ 
              | |    / ____|                  | |
 __      _____| |__ | |     _ __ __ ___      _| |
 \ \ /\ / / _ \ '_ \| |    | '__/ _` \ \ /\ / / |
  \ V  V /  __/ |_) | |____| | | (_| |\ V  V /| |
   \_/\_/ \___|_.__/ \_____|_|  \__,_| \_/\_/ |_|
                                                 
    author:  {AsciiColors.HEADER}{author}{AsciiColors.ENDC}
    version: {AsciiColors.HEADER}{version}{AsciiColors.ENDC}
    """)
    
    
class DictParser(argparse.Action):
    """this class is used to convert an argument directly into a dict using the format key=value&key=value"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        try:
            for query in values.split("&"):
                key, val = query.split('=')
                getattr(namespace, self.dest)[key] = val    
        except:
            show_error(f"uanble to parse {values} due to incorrect format ", "DictParser")


class ProxyParser(argparse.Action):
    """this class is used to convert an argument directly into a dict using the format key;value,key=value"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, dict())
        try:
            for query in values.split(","):
                key, val = query.split(';')
                getattr(namespace, self.dest)[key] = val    
        except:
            show_error(f"uanble to parse {values} due to incorrect format ", "ProxyParser")

class ListParser(argparse.Action):
    """this class is used to convert an argument directly into a comma separated list"""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, list())
        try:
            for val in values.split(','):
                getattr(namespace, self.dest).append(val)
        except:
            show_error(f"unable to parse {values} due to incorrect format", "class::ListParser")
 

class AsciiColors:
    HEADER  = '\033[95m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL    = '\033[91m'
    ENDC    = '\033[0m'


def parse_arguments():
    """ return parsed arguments """

    parser = argparse.ArgumentParser(prog="./webCrawler.py", 
                                     usage="./WebCrawler.py [options] -u {url} ",
                                     description="a simple python web crawler", 
                                     epilog="https://github.com/mind2hex/")
    
    # general args
    parser.add_argument("-u", "--url",         metavar="", required=True, help=f"target url. ex --> http://localhost/")
    parser.add_argument("-H", "--headers",     metavar="", default={},   action=DictParser,  help="set HTTP headers. ex --> 'Header1=lol&Header2=lol'")    
    parser.add_argument("-P", "--proxies",     metavar="", default={},   action=ProxyParser, help="set proxies.      ex --> 'http;http://proxy1:8080,https;http://proxy2:8000'") 
    parser.add_argument("-D", "--download",    metavar="", default=None, action=ListParser,  help="coma separated extension files to download. ex --> jpg,pdf,png")
    parser.add_argument("-x", "--exclude-url", metavar="", default=None, action=ListParser,  help=f"comma separated domains to exclude. ex --> google.com,youtube.com")
    parser.add_argument("-U", "--user-agent",  metavar="", default="yoMama", help="specify user agent")
    parser.add_argument("-N", "--no-follow",    action="store_false", help="follow redirections")
    parser.add_argument("--rand-user-agent", action="store_true", help="randomize user-agent")
    parser.add_argument("--usage",           action="store_true", help="show usage examples")    
    parser.add_argument("--ignore-errors",   action="store_true", help="ignore connection errors")
    parser.add_argument("-d", "--depth",       metavar="", default=1, type=int, help=f"")
    
    # performance args
    performance = parser.add_argument_group("performance options")
    performance.add_argument("-rt","--retries",  metavar="", type=int, default=0,  help="retries per connections if connection fail [default 0]")

    # debugging args
    debug = parser.add_argument_group("debugging options")
    debug.add_argument("-v", "--verbose", action="store_true", help="show verbose messages")
    debug.add_argument("--debug",         action="store_true", help="show debugging messages")
    debug.add_argument("-o", "--output",  metavar="", type=argparse.FileType('w'), help="save output to a file")
    debug.add_argument("-q", "--quiet",   action="store_true", help="dont show config before execution")

    parsed_arguments               = parser.parse_args()        

    # indexed_urls is used to store already requested urls and avoid an infinite loop
    parsed_arguments.indexed_urls = list()

    # parsing user agents
    parsed_arguments.UserAgent_wordlist = ['Mozilla/1.22 (compatible; MSIE 2.0d; Windows NT)', 
                     'Mozilla/2.0 (compatible; MSIE 3.02; Update a; Windows NT)', 
                     'Mozilla/4.0 (compatible; MSIE 4.01; Windows NT)',
                     'Mozilla/4.0 (compatible; MSIE 5.5; Windows NT 4.0)', 
                     'Mozilla/4.79 [en] (WinNT; U)', 
                     'Mozilla/5.0 (Windows; U; WinNT4.0; en-US; rv:0.9.2) Gecko/20010726 Netscape6/6.1', 
                     'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.9.0.4) Gecko/2008102920 Firefox/3.0.4', 
                     'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; .NET CLR 1.1.4322; .NET CLR 2.0.50727; .NET CLR 3.0.04506.30; .NET CLR 3.0.04506.648; .NET CLR 3.5.21022)', 
                     'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US; rv:1.8.1.19) Gecko/20081204 SeaMonkey/1.1.14', 
                     'Mozilla/5.0 (SymbianOS/9.2; U; Series60/3.1 NokiaE90-1/210.34.75 Profile/MIDP-2.0 Configuration/CLDC-1.1 ) AppleWebKit/413 (KHTML, like Gecko) Safari/413', 
                     'Mozilla/5.0 (iPhone; U; CPU iPhone OS 2_2 like Mac OS X; en-us) AppleWebKit/525.18.1 (KHTML, like Gecko) Version/3.1.1 Mobile/5G77 Safari/525.20', 
                     'Mozilla/5.0 (Linux; U; Android 1.5; en-gb; HTC Magic Build/CRB17) AppleWebKit/528.5+ (KHTML, like Gecko) Version/3.1.2 Mobile Safari/525.20.1', 
                     'Opera/9.27 (Windows NT 5.1; U; en)', 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.27.1 (KHTML, like Gecko) Version/3.2.1 Safari/525.27.1', 
                     'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET CLR 1.0.3705; .NET CLR 1.1.4322)', 
                     'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/0.4.154.25 Safari/525.19', 
                     'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/525.19 (KHTML, like Gecko) Chrome/1.0.154.48 Safari/525.19', 
                     'Wget/1.8.2', 'Mozilla/5.0 (PLAYSTATION 3; 1.00)', 
                     'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; (R1 1.6))', 
                     'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-GB; rv:1.8.1.1) Gecko/20061204 Firefox/2.0.0.1', 
                     'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-GB; rv:1.9.0.10) Gecko/2009042316 Firefox/3.0.10 (.NET CLR 3.5.30729) JBroFuzz/1.4', 
                     'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SLCC1; .NET CLR 2.0.50727; Media Center PC 5.0; .NET CLR 3.0.04506)', 
                     'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.7.12) Gecko/20050923 CentOS/1.0.7-1.4.1.centos4 Firefox/1.0.7', 
                     'Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 6.0; SLCC1; .NET CLR 2.0.50727)', 
                     'Mozilla/5.0 (Windows; U; Windows NT 6.0; en-GB; rv:1.9.0.5) Gecko/2008120122 Firefox/3.0.5', 
                     'Mozilla/5.0 (X11; U; SunOS i86pc; en-US; rv:1.7) Gecko/20070606', 'Mozilla/5.0 (X11; U; SunOS i86pc; en-US; rv:1.8.1.14) Gecko/20080520 Firefox/2.0.0.14', 
                     'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.5; en-US; rv:1.9.0.5) Gecko/2008120121 Firefox/3.0.5']        
    
    return parsed_arguments


def usage():
    """ Only show ussage messages """
    print("No usage messages yet")
    exit(0)


def get_file_lines(file):
    """ retorna la cantidad de lineas de un archivo """

    # detecting encoding
    with open(file, 'rb') as f:
        codification = detect_encoding(f.read())['encoding']

    # getting lines
    with open(file, 'r', encoding=codification) as f:
        total = sum(1 for line in f)
        
    return total   


def validate_arguments(args):
    """ validate_arguments checks that every argument is valid or in the correct format """

    validate_url(args.url)

def validate_url(url, supress_error=False):
    """ validate url using URLValidator from django
        if supress_error == True, then returns False instead of showing error
    """
    val = URLValidator()    
    try:
        val(url)
    except:
        if not supress_error :
            show_error(f"Error while validating url --> {url}", f"function::{currentframe().f_code.co_name}")
        return False
    return True


def initial_checks(args):
    """ Initial checks before proceeds with the program execution"""
    check_target_connectivity(args.url)
    check_proxy_connectivity(args.url, args.proxies)


def check_target_connectivity(target_url):
    # testing target connection
    try:
        requests.get(target_url, allow_redirects=False)
    except requests.exceptions.ConnectionError:
        show_error(f"Failed to establish a new connection to {target_url}", f"function::{currentframe().f_code.co_name}")


def check_proxy_connectivity(url, pr):
    # testing proxy connection
    if len(pr) > 0:
        try:
            requests.get(url+"/proxy_test", proxies=pr)
        except :
            show_error(f"Proxy server is not responding", f"function::{currentframe().f_code.co_name}")


def show_error(msg, origin):
    print(f"\n {origin} --> {AsciiColors.FAIL}error{AsciiColors.ENDC}")
    print(f" [X] {AsciiColors.FAIL}{msg}{AsciiColors.ENDC}")
    exit(-1)


def show_config(args):
    print(f"[!] %-20s %s"%(f"{AsciiColors.HEADER}GENERAL{AsciiColors.ENDC}", "="*40))
    print("%-20s:%s"%("TARGET",args.url))
    print("%-20s:%s"%("DEPTH",args.depth))
    print("%-20s:%s"%("HEADERS", str(args.headers)))    
    print("%-20s:%s"%("PROXIES", str(args.proxies)))    
    print("%-20s:%s"%("USER-AGENT", str(args.user_agent)))    
    print("%-20s:%s"%("RAND-USER-AGENT",str(args.rand_user_agent)))    
    print("%-20s:%s"%("FOLLOW REDIRECT",str(args.no_follow)))    
    print("%-20s:%s"%("IGNORE ERRORS",str(args.ignore_errors)))    
    print()
    print(f"[!] %-20s %s"%(f"{AsciiColors.HEADER}PERFORMANCE{AsciiColors.ENDC}", "="*40))
    print("%-20s:%s"%("RETRIES",args.retries))    
    print()
    print(f"[!] %-20s %s"%(f"{AsciiColors.HEADER}DEBUGGING{AsciiColors.ENDC}", "="*40))
    print("%-20s:%s"%("VERBOSE",args.verbose))    
    print("%-20s:%s"%("DEBUG",args.debug))    
    print("%-20s:%s"%("OUTPUT",args.output))    
    print()
    sleep(2)


def crawler(args, current_target, current_depth):
    html = requests.get(current_target, allow_redirects=args.no_follow).content
    
    soup = BeautifulSoup(html, 'html.parser')
    

    # current_urls store all urls found in current_target
    current_urls = list()
    elements = soup.find_all(src=True) + soup.find_all(href=True)
    for element in elements:
        if 'src' in element.attrs:
            if not validate_url(element['src'], supress_error=True):
                aux = f"{args.url}{element['src'].lstrip('/')}"
            else:
                aux = element['src']
        if 'href' in element.attrs:
            if not validate_url(element['href'], supress_error=True):
                aux = f"{args.url}{element['href'].lstrip('/')}"
            else:
                aux = element['href']
        current_urls.append(aux)
    
    current_urls = list(set(current_urls))
    

    for url in current_urls:
        if (url not in args.indexed_urls) and (current_depth < args.depth):
            # showing new url found and where it was found
            print(f"[!] %-100s -> %s"%(url[:100], current_target))
            args.indexed_urls.append(url)
            if not is_media_file(urlparse(url).path) and (urlparse(url).netloc == urlparse(args.url).netloc):
                crawler(args, url, current_depth + 1)
    
    return 0


def is_media_file(url_path):
    ext = url_path.split('.')[-1].lower()
    media_exts = ['svg', 'js', 'mp4', 'mp3', 'avi', 'jpg', 'jpeg', 'png', 'pdf', 'gif', 'webp', 'xml']
    return True if ext in media_exts else False


def main():
    banner()

    if ("--usage" in argv):
        usage()

    parsed_arguments = parse_arguments()
    
    validate_arguments(parsed_arguments)    

    initial_checks(parsed_arguments)

    if (parsed_arguments.quiet == False):
        show_config(parsed_arguments)    

    crawler(parsed_arguments, parsed_arguments.url, 0)

    return 0


if __name__ == "__main__":
    try:
        exit(main())
    except KeyboardInterrupt:
        show_error("User Keyboard Interrupt", "main")


##  FUNCIONALIDADES PARA AGREGAR
#   - basic auth
#   - implementar multiproceso combinado con multihilo

##  ERRORES O BUGS PARA CORREGIR
#   - refactorizar algunas funciones                                                                                                                                                                                                         
#   - mejorar un poco el output                                                                                                                                                                                                              
#   - actualizar usage()
#   - si la ventana reduce su tamano, el formato de salida se va a estropear.
#   - al intentar parsear con bs un xml muestra un error