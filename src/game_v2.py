# imports
import asyncio
import logging
from datetime import datetime
import json
import random

from pywebio import start_server
from pywebio import config
from pywebio.input import *
from pywebio.output import *
from pywebio.session import defer_call, info as session_info, run_async


# const settings
MAX_MESSAGES_CNT = 5000
MAX_PLAYER_ON_TABLE = 12
MIN_PLAYER_TO_START = 2
DATA_FILE = "save_test1.json"
LOG_FILE = "log.txt"
DESK_CODES = ""
AUTO_RELOAD_CHIPS_WHEN_LESS_THAN = 100
DEFAULT_BUYIN = 2000
THINK_TIME = 20
SB_BET = 10
BB_BET = 20

all_suits = [0, 1, 2, 3]
all_suits_name = ["黑桃♠", "红桃♥", "方片♦", "梅花♣"]
all_ranks = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
all_ranks_name = [None,None,"2", "3", "4", "5", "6", "7", "8", "9", "10","J", "Q", "K", "A"]



# log
logger = logging.getLogger()
logger.setLevel(logging.INFO)

fh = logging.FileHandler(LOG_FILE, mode='a')
fh.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

logger.addHandler(fh)



def get_card_name(a_card):
    return "{}{}".format(all_suits_name[a_card[1]],all_ranks_name[a_card[0]])

def get_card_img(a_card):
    if(a_card == None):
        return ""
    else:
        return "poker_imgs/p_{}_{}.jpg".format(a_card[0],1 + a_card[1])
    
    
def key_card_suits(a_card):
    return a_card[1] * 100 + a_card[0]

def key_card_ranks(a_card):
    return a_card[0] * 100 + a_card[1]

def get_hand_power(a_hand):
    if(len(a_hand) != 7):
        print("hand_len ERROR :{}, which should be 7".format(len(a_hand)))
        return None
    # check if Straight Flush
    # power :[8,min straight rank]
    a_hand.sort(key=key_card_suits, reverse=True)
    cur_suit = -1
    has_Ace = False
    last_rank = -1
    cur_len = 0
    for i in range(0, len(a_hand)):
        # check if new suit
        if(a_hand[i][1] != cur_suit):
            if(cur_len == 4 and last_rank == 2 and has_Ace):
                # bingo
                return [8, 1]
            cur_suit = a_hand[i][1]
            if(a_hand[i][0] == 14):
                # has Ace
                has_Ace = True
            else:
                has_Ace = False
            last_rank = a_hand[i][0]
            cur_len = 1
        else:
            if(a_hand[i][0] == last_rank - 1):
                cur_len = cur_len + 1
                if(cur_len == 5):
                    # bingo
                    return [8, a_hand[i][0]]
            else:
                cur_len = 1
            last_rank = a_hand[i][0]
    if(cur_len == 4 and last_rank == 2 and has_Ace):
        # bingo
        return [8, 1]

    # check if Four of a Kind
    # power :[7,four of kind's rank,other hight card's rank ]
    a_hand.sort(key=key_card_ranks, reverse=True)
    cur_rank = -1
    cur_rep = 0
    for i in range(0, len(a_hand)):
        if(a_hand[i][0] == cur_rank):
            cur_rep = cur_rep + 1
            if(cur_rep == 4):
                # bingo,and to get the other one card
                for i2 in range(0, len(a_hand)):
                    if(a_hand[i2][0] != cur_rank):
                        return [7, cur_rank, a_hand[i2][0]]
        else:
            cur_rep = 1
            cur_rank = a_hand[i][0]

    # check if Full House
    # power :[6,three kind rank,highest pair rank]
    three_kind_rank = -1
    pair_rank = -1
    cur_rank = -1
    cur_rep = 0
    for i in range(0, len(a_hand)):
        if(a_hand[i][0] == cur_rank):
            cur_rep = cur_rep + 1
        else:
            if(cur_rep == 3 and cur_rank > three_kind_rank):
                three_kind_rank = cur_rank
            else:
                if(cur_rep == 2 and cur_rank > pair_rank):
                    pair_rank = cur_rank
            cur_rank = a_hand[i][0]
            cur_rep = 1
    if(three_kind_rank != -1 and pair_rank != -1):
        # bingo
        return [6, three_kind_rank, pair_rank]

    # check if Flush
    # power :[5,1-5 rank of the flush....]
    a_hand.sort(key=key_card_suits, reverse=True)
    suit_first_index = -1
    cur_suit = -1
    cur_len = 0
    for i in range(0, len(a_hand)):
        if(a_hand[i][1] == cur_suit):
            cur_len = cur_len + 1
            if(cur_len == 5):
                # bingo
                return [5, a_hand[suit_first_index][0],
                        a_hand[suit_first_index + 1][0],
                        a_hand[suit_first_index + 2][0],
                        a_hand[suit_first_index + 3][0],
                        a_hand[suit_first_index + 4][0]]
        else:
            cur_len = 1
            cur_suit = a_hand[i][1]
            suit_first_index = i

    # check if Straight
    # power :[4,min straight rank]
    a_hand.sort(key=key_card_ranks, reverse=True)
    last_rank = -1
    cur_len = 0
    has_Ace = False
    if(a_hand[0][0] == 14):
        has_Ace = True
    for i in range(0, len(a_hand)):
        if(a_hand[i][0] == last_rank):
            continue
        if(a_hand[i][0] == last_rank - 1):
            cur_len = cur_len + 1
            last_rank = a_hand[i][0]
            if(cur_len == 5):
                # bingo
                return [4, last_rank]
            if (cur_len == 4 and a_hand[i][0] == 2 and has_Ace):
                # bingo
                return [4, 1]
        else:
            cur_len = 1
            last_rank = a_hand[i][0]

    # check if Three of a Kind
    # power :[3,three kind rank,other two high,,]
    first_high = -1
    if(three_kind_rank != -1):
        for i in range(0, len(a_hand)):
            if(first_high == -1 and a_hand[i][0] != three_kind_rank):
                first_high = a_hand[i][0]
            else:
                if(first_high != -1
                   and a_hand[i][0] != three_kind_rank
                   and a_hand[i][0] != first_high):
                    return [3, three_kind_rank, first_high, a_hand[i][0]]

    # check if Two Pair
    # power :[2,Top Pair rank,Second Pair Rank,High Rank]
    if(pair_rank != -1):
        top_pair_rank = -1
        for i in range(0, len(a_hand)):
            if(i != len(a_hand) - 1 and a_hand[i][0] == a_hand[i + 1][0]):
                if(top_pair_rank == -1):
                    top_pair_rank = a_hand[i][0]
                else:
                    for i2 in range(0, len(a_hand)):
                        if(a_hand[i2][0] != top_pair_rank
                           and a_hand[i2][0] != a_hand[i][0]):
                            return [2, top_pair_rank,
                                    a_hand[i][0], a_hand[i2][0]]

    # check if Pair
    # power :[1,Top Pair rank,First High Rank,Second High Rank,Third High Rank]
    if(pair_rank != -1):
        first_high = -1
        second_high = -1
        for i in range(0, len(a_hand)):
            if(a_hand[i][0] == pair_rank):
                continue
            if(first_high == -1):
                first_high = a_hand[i][0]
                continue
            if(second_high == -1):
                second_high = a_hand[i][0]
                continue
            return [1, pair_rank, first_high, second_high, a_hand[i][0]]

    # check if High Card
    # power :[0,Top Pair rank,First High Rank,Second High Rank,Third High Rank]
    return [0, a_hand[0][0], a_hand[1][0],
            a_hand[2][0], a_hand[3][0],
            a_hand[4][0], a_hand[5][0]]


power_coefficient = [pow(16, 6), pow(16, 5), pow(16, 4),
                     pow(16, 3), pow(16, 2), pow(16, 1), 1]


def key_hand_power(hand_power):
    result = 0
    for i in range(0, len(hand_power)):
        result = result + hand_power[i] * power_coefficient[i]
    return result



## Desk Info
class DESK_STATES:
    NOT_CREATED = 0
    WAIT_TO_START = 10
    WAIT_TO_START_WAITING = 11
    PREFLOP = 20
    FLOP = 30
    TURN = 40
    RIVER = 50


class DeskInfo:
    
    desk_code = ""
    info_version = 0
    off_round_actions_list = []
    desk_state = DESK_STATES.NOT_CREATED
    players_online = []
    seats = [None for i in range(0, MAX_PLAYER_ON_TABLE)]
    desk_cards = []
    pot = 0
    highest_bet = 0
    end_index = 0
    BTN_index = 0
    SB_index = 0
    BB_index = 0
    UTG_index = 0
    wait_index = 0
    all_done_and_wait_for_next_round = False
    wait_to_start_waiting_time = 0
    waiting_seconds = 0
    
    def __init__(self, desk_code):
        self.desk_code = desk_code
        
    def refresh_table(self):
        self.info_version = self.info_version + 1
        
    def num_of_player_in_seat(self):
        result = 0
        for i in range(0,MAX_PLAYER_ON_TABLE):
            if(self.seats[i] != None):
                result = result + 1
        return result
    
desk_info = DeskInfo(DESK_CODES)



# player info

free_player_id = 10000

    
class PlayerInfo:
    
    player_name = ""
    player_id = 0
    password = ""
    player_floating_surplus = 0
    sit_at = -1
    sit_as = ""
    player_chips = DEFAULT_BUYIN
    player_investment = 0
    player_equity = 0
    player_equity_final = 0
    has_fold = False
    player_bet = 0
    do_raise = False
    in_deciding = False
    hand_cards = []
    key_hand_power = 0
    input_state = -1
    input_version = 0
    unsend_chat_text = ""
    setting_bet = 0
    online = False
    
    def __init__(self, player_name, password, player_id = 0, player_floating_surplus = 0):
        global free_player_id
        self.player_name = player_name
        self.password = password
        if(player_id == 0):
            self.player_id = free_player_id
            free_player_id = free_player_id + 1
        else:
            self.player_id = player_id
            self.player_floating_surplus = player_floating_surplus
            
    def __str__(self):
        temp_dict = dict()
        temp_dict["player_name"] = self.player_name
        temp_dict["player_id"] = self.player_id
        temp_dict["player_floating_surplus"] = self.player_floating_surplus
        temp_dict["online"] = self.online
        temp_dict["sit_at"] = self.sit_at
        temp_dict["input_state"] = self.input_state
        temp_dict["password"] = self.password
        return str(temp_dict)
    
    def refresh_input(self,input_state = None):
        self.input_version = self.input_version + 1
        if(input_state != None):
            self.input_state = input_state

            
players_info_by_name = dict()


def save_dict_to_json_file(data,file):
    with open(file, "w") as outfile:
        json.dump(data, outfile)
        

def load_json_file_to_dict(file):
    with open(file) as json_file:
        data = json.load(json_file)
    return data


def load_persist_data():
    global free_player_id
    global players_info_by_name
    persist_data = load_json_file_to_dict(DATA_FILE)
    free_player_id = persist_data["free_player_id"]
    for player_name in persist_data["players_info_by_name"].keys():
        player_info = PlayerInfo(
            persist_data["players_info_by_name"][player_name]["player_name"],
            persist_data["players_info_by_name"][player_name]["password"],
            persist_data["players_info_by_name"][player_name]["player_id"],
            persist_data["players_info_by_name"][player_name]["player_floating_surplus"],
        )
        players_info_by_name[player_info.player_name] = player_info
        

def save_persist_data():
    global free_player_id
    global players_info_by_name
    persist_data = dict()
    persist_data["free_player_id"] = free_player_id
    persist_data["players_info_by_name"] = dict()
    
    for a_player_info in players_info_by_name.values():
        persist_data["players_info_by_name"][a_player_info.player_name] = {
            "player_name":a_player_info.player_name,
            "player_id":a_player_info.player_id,
            "player_floating_surplus":a_player_info.player_floating_surplus,
            "password":a_player_info.password
        }
    
    save_dict_to_json_file(persist_data,DATA_FILE)
    
    
# message manage
class Message:
    from_whom = ""
    content = ""
    send_time = 0
    do_toast = False
    to_whom = "ALL"
    
    def __init__(self, from_whom, content, to_whom = "ALL",do_toast= False):
        self.from_whom = from_whom
        self.content = content
        self.send_time = datetime.now()
        self.do_toast = do_toast
        self.to_whom = to_whom
    
global_msgs = [] #

def create_a_message(from_whom, content, to_whom = "ALL", do_toast = True):
    global global_msgs
    msg = Message(from_whom,content,to_whom,do_toast)
    global_msgs.append(msg)
    logger.info("消息： `{}` : {}".format(msg.from_whom,msg.content))

async def msg_manager(this_player_info):
    global desk_info
    global players_info_by_name
    global global_msgs
    
    last_idx = 0
    while True:
        await asyncio.sleep(0.2)
        for msg in global_msgs[last_idx:]:
            if(msg.to_whom == "ALL" or msg.to_whom == this_player_info.name):
                time_str = msg.send_time.strftime("%H:%M:%S")
                put_markdown("`{}` `{}` : {}".format(time_str,msg.from_whom,msg.content), sanitize = True, scope = 'msg-box')
                if(last_idx !=0 and msg.do_toast):
                    toast('{} : {}'.format(msg.from_whom,msg.content))

        # remove expired message
        if len(global_msgs) > MAX_MESSAGES_CNT:
            global_msgs = global_msgs[len(global_msgs) // 2:]

        last_idx = len(global_msgs)
        
        


async def info_table_manager(this_player_info,this_desk_info):

    global global_table_version
    current_info_version = -1

    while True:
        await asyncio.sleep(0.1)
        if(current_info_version == this_desk_info.info_version):
            continue
        current_info_version = this_desk_info.info_version

        table = []
        
        #你的状态
        your_state_str = ""
        if(this_player_info.input_state == INPUT_STATES.INPUT_STAND):
            your_state_str = "你正站在桌边观战"
        elif(this_player_info.input_state == INPUT_STATES.INPUT_WAIT_OPEN and this_desk_info.desk_state == DESK_STATES.NOT_CREATED):
            your_state_str = "等待人数足够{}后开始新的一局".format(MIN_PLAYER_TO_START)
        elif(this_player_info.input_state == INPUT_STATES.INPUT_WAIT_OPEN and this_player_info.has_fold):
            your_state_str = "你已弃牌，观看等待本局结束后开始新的一局"
        elif(this_player_info.input_state == INPUT_STATES.INPUT_WAIT_OTHERS and not this_player_info.has_fold):
            your_state_str = "等待 {} 决策中".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
        elif(this_player_info.input_state == INPUT_STATES.INPUT_OPEN):
            your_state_str = "轮到你决策了"

        #你的手牌
        your_hand_cards_str = ""
        if(len(this_player_info.hand_cards) == 0):
            your_hand_cards_str = "还未发牌"
        else:
#             your_hand_cards_str = "{},{}".format(get_card_name(this_player_info.hand_cards[0]),get_card_name(this_player_info.hand_cards[1]))
            your_hand_cards_str = put_table([[put_image(open(get_card_img(this_player_info.hand_cards[0]), 'rb').read(),width='50px'),
                                              put_image(open(get_card_img(this_player_info.hand_cards[1]), 'rb').read(),width='50px')]])
            
        #桌面状态
        desk_state_str = ""
        if(this_desk_info.desk_state == DESK_STATES.WAIT_TO_START):
            desk_state_str = "等待开始..."
        elif(this_desk_info.desk_state == DESK_STATES.PREFLOP):
            desk_state_str = "翻牌前阶段,{} 决策中...".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
        elif(this_desk_info.desk_state == DESK_STATES.FLOP):
            desk_state_str = "翻牌阶段,{} 决策中...".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
        elif(this_desk_info.desk_state == DESK_STATES.TURN):
            desk_state_str = "转牌阶段,{} 决策中...".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
        elif(this_desk_info.desk_state == DESK_STATES.RIVER):
            desk_state_str = "河牌阶段,{} 决策中...".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
            
        #翻牌
        desk_flop_cards_str = ""
        if(len(this_desk_info.desk_cards) == 5):
            if(this_desk_info.desk_state in [DESK_STATES.WAIT_TO_START,DESK_STATES.FLOP,DESK_STATES.TURN,DESK_STATES.RIVER]):
#                 desk_flop_cards_str = "{},{},{}".format(get_card_name(this_desk_info.desk_cards[0]),get_card_name(this_desk_info.desk_cards[1]),get_card_name(this_desk_info.desk_cards[2]))
                desk_flop_cards_str = put_table([[put_image(open(get_card_img(this_desk_info.desk_cards[0]), 'rb').read(),width='50px'),
                                                  put_image(open(get_card_img(this_desk_info.desk_cards[1]), 'rb').read(),width='50px'),
                                                  put_image(open(get_card_img(this_desk_info.desk_cards[2]), 'rb').read(),width='50px')
                                                 ]])
            else:
                desk_flop_cards_str = put_table([[put_image(open("poker_imgs/p_back.png", 'rb').read(),width='50px'),
                                                  put_image(open("poker_imgs/p_back.png", 'rb').read(),width='50px'),
                                                  put_image(open("poker_imgs/p_back.png", 'rb').read(),width='50px')
                                                  ]])
        #转牌
        desk_turn_cards_str = ""
        if(len(this_desk_info.desk_cards) == 5):
            if(this_desk_info.desk_state in [DESK_STATES.WAIT_TO_START,DESK_STATES.TURN,DESK_STATES.RIVER]):
#                 desk_turn_cards_str = "{}".format(get_card_name(this_desk_info.desk_cards[3]))
                desk_turn_cards_str = put_image(open(get_card_img(this_desk_info.desk_cards[3]), 'rb').read(),width='50px')
            else:
                desk_turn_cards_str = put_image(open("poker_imgs/p_back.png", 'rb').read(),width='50px')
        #河牌
        desk_river_cards_str = ""
        if(len(this_desk_info.desk_cards) == 5):
            if(this_desk_info.desk_state in [DESK_STATES.WAIT_TO_START,DESK_STATES.RIVER]):
#                 desk_river_cards_str = "{}".format(get_card_name(this_desk_info.desk_cards[4]))
                desk_river_cards_str = put_image(open(get_card_img(this_desk_info.desk_cards[4]), 'rb').read(),width='50px')
            else:
                desk_river_cards_str = put_image(open("poker_imgs/p_back.png", 'rb').read(),width='50px')
        #信息面板
        table = [
            ['你的状态', span(your_state_str, col = 3)],
            ['你的筹码', this_player_info.player_chips, '累计盈亏',this_player_info.player_floating_surplus],
            ['你的手牌', span(your_hand_cards_str, col = 3)],
            [span(put_markdown('**桌面信息**'), col = 4)],
            ['牌桌状态', span(desk_state_str, col = 3)],
            ['翻牌', span(desk_flop_cards_str, col = 3)],
            ['转/河牌', span(put_table([[desk_turn_cards_str,desk_river_cards_str]]), col = 3)],
            ['当前底池',span(this_desk_info.pot, col = 3)],
            ['玩家', '位置','操作','筹码'],
        ]
        
        def short_player_state_str(a_player_info):
            state_str = ""
            if(a_player_info.has_fold):
                state_str = "已弃"
            elif(a_player_info.player_chips == 0):
                state_str = "ALL-IN {}".format(a_player_info.player_bet)
            elif(a_player_info.in_deciding):
                state_str = put_loading().style('width:1.5em; height:1.5em')
            elif(a_player_info.player_bet == 0):
                state_str = "待决策"
            elif(a_player_info.do_raise):
                state_str = "下注 {}".format(a_player_info.player_bet)
            elif(not a_player_info.do_raise):
                state_str = "下注 {}".format(a_player_info.player_bet)
            return state_str
        
        #玩家信息
        for i in range(0,MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] != None):
                state_str = ""
                table.append([
                    this_desk_info.seats[i].player_name,
                    this_desk_info.seats[i].sit_as,
                    short_player_state_str(this_desk_info.seats[i]),
                    this_desk_info.seats[i].player_chips
                ])
        
        with use_scope('info-table', clear=True):
            put_table(table,header = [span('你的信息', col = 4)])
            
            
def basic_layout():
    if(session_info.user_agent.is_mobile):
        put_text("检测到手机登录")
    with use_scope('head-area', clear=True):
        put_markdown("")
    with use_scope('info-table', clear=True):
        put_markdown("")
    with use_scope('msg-area', clear=True):
        with use_scope('msg-box', clear=True):
            put_markdown("")
    with use_scope('input-area', clear=True):
        put_markdown("")
        
        
        

# login
async def player_login():
    
    global desk_info
    global players_info_by_name
    global global_msgs
    
    def my_name_validate(name):
        
        global players_info_by_name
        
        if(name == ""):
            return '名字不能为空'
        
        for test_text in ['系统','ALL',' ',':','{','}','[',']',',','\'','\\']:
            if(test_text in name):
                return '天整些骚名字哦'
        
        player_info = players_info_by_name.get(name)
        if(player_info != None and player_info.online):
            tip = '玩家 {} 已经在线，需要的话可以先从原有设备退出'.format(name)
            return tip
        
    
    def new_password_validate(data):
        
        if(data['CMD'] == "重选用户名"):
            return None
        
#         if(data['password1'] == ""):
#             return ('password1','密码不能为空')
                    
        if(data['password1'] != data['password2']):
            return ('password2','两次密码不一致')
    
    
    class LOGIN_STATES:
        ROOM_CODE = 0
        NAME = 10
        PASSWORD = 20
        PASSWORD_NEW = 21
    
#     login_state = LOGIN_STATES.ROOM_CODE
    login_state = LOGIN_STATES.NAME
    
    input_player_name = ""
    input_player_password = ""
    player_info = None
    
    while True:
        
        if(login_state == LOGIN_STATES.ROOM_CODE):            
            
            with use_scope('head-area', clear=True):
                input_room_code = await input("来对一下口令：", type = PASSWORD)
                
            if(input_room_code != DESK_CODES):
                toast("哦豁，没对上")
            else:
                login_state = LOGIN_STATES.NAME
                continue

        elif(login_state == LOGIN_STATES.NAME):
            with use_scope('head-area', clear=True):
                put_markdown("欢迎核心！")
                input_player_name = await input("新建/登录 用户名",required=True, validate = my_name_validate)
            player_info = players_info_by_name.get(input_player_name)

            if(player_info == None):
                login_state = LOGIN_STATES.PASSWORD_NEW
                continue
            else:
                login_state = LOGIN_STATES.PASSWORD

        elif(login_state == LOGIN_STATES.PASSWORD):
            with use_scope('head-area', clear=True):
                put_markdown("用户名 {} 存在且不在线，输入密码".format(input_player_name))
                input_data = await input_group("设置密码：",[
                    input('输入密码', name = 'password', type = PASSWORD),
                    actions(name = 'CMD', buttons = ['确认','重选用户名'])
                ])
            if(input_data['CMD'] == '确认'):
                input_player_password = input_data['password']
                player_info = players_info_by_name.get(input_player_name)
                if(player_info == None):
                    toast("ERROR:players_info_by_name中找不到player_info")
                    continue
                if(player_info.online):
                    toast("玩家突然在线了，需要的话可以先从原有设备退出")
                    login_state = LOGIN_STATES.NAME
                    continue
                if(player_info.password == input_player_password):
                    return player_info
                else:
                    toast("密码不正确")
                    login_state = LOGIN_STATES.PASSWORD

            elif(input_data['CMD'] == '重选用户名'):
                login_state = LOGIN_STATES.NAME
                continue

        elif(login_state == LOGIN_STATES.PASSWORD_NEW):
            with use_scope('head-area', clear=True):
                put_markdown("用户名 {} 还不存在，输入密码新建一个吧\n（注：密码是明文保存的，用个水点的密码。密码主要目的是防别人误登）".format(input_player_name))
                input_data = await input_group("设置密码：",[
                    input('设置密码', name = 'password1', type = PASSWORD),
                    input('确认密码', name = 'password2', type = PASSWORD),
                    actions(name = 'CMD', buttons = ['确认','重选用户名'])
                ], validate = new_password_validate)

            if(input_data['CMD'] == '确认'):
                input_player_password = input_data['password1']
                player_info = players_info_by_name.get(input_player_name)
                if(player_info == None):
                    player_info = PlayerInfo(input_player_name, input_player_password)
                    players_info_by_name[input_player_name] = player_info
                    save_persist_data()
                    return player_info
                else:
                    toast("哦豁，此用户名刚被别人注册了")
                    login_state = LOGIN_STATES.NAME
                    continue
            elif(input_data['CMD'] == '重选用户名'):
                login_state = LOGIN_STATES.NAME
                continue
                
                

        
def RandomDeal(this_desk_info):
    
    left_cards = []
    for suit in all_suits:
        for rank in all_ranks:
            left_cards.append((rank, suit))
            
    random.shuffle(left_cards)
    deal_at = 0
    
    for i in range(0, MAX_PLAYER_ON_TABLE):
        if(this_desk_info.seats[i] != None):
            this_desk_info.seats[i].hand_cards.append(left_cards[deal_at])
            this_desk_info.seats[i].hand_cards.append(left_cards[deal_at + 1])
            deal_at = deal_at + 2
            logger.info('发牌：{} 玩家: {}'.format(this_desk_info.seats[i].player_name,str(this_desk_info.seats[i].hand_cards)))

    for i in range(0, 5):
        this_desk_info.desk_cards.append(left_cards[deal_at])
        deal_at = deal_at + 1

    logger.info('发牌：桌面: {}'.format(str(this_desk_info.desk_cards)))
            
    
def player_join(this_player_info):
    global desk_info
    global players_info_by_name

    this_player_info.online = True
    desk_info.players_online.append(this_player_info)
    desk_players_names = [player_info.player_name for player_info in desk_info.players_online]
    create_a_message("📢系统", '{} 进入了房间'.format(this_player_info.player_name))
    create_a_message("📢系统", '当前在线: {} 人:{}'.format(len(desk_info.players_online),str(desk_players_names)),do_toast= False)
    logger.info('{}登录成功！当前在线: {} 人:{}'.format(this_player_info.player_name,
                                              len(desk_info.players_online),
                                              str(desk_players_names)))

    if(this_player_info.input_state != -1):##玩家之前已经在了,重连
        this_player_info.refresh_input()
        logger.info('player {} back to desk'.format(this_player_info.player_name))
    else:
        logger.info('player {} new to stand'.format(this_player_info.player_name))
        this_player_info.refresh_input(INPUT_STATES.INPUT_STAND)

def player_leave(this_player_info):
    global desk_info
    global players_info_by_name

    this_player_info.online = False
    desk_info.players_online.remove(this_player_info)
    desk_players_names = [player_info.player_name for player_info in desk_info.players_online]
    create_a_message("📢系统", '{} 离开了房间'.format(this_player_info.player_name))
    logger.info('{}离开了房间！当前在线: {} 人:{}'.format(len(desk_info.players_online),str(desk_players_names)))
    
    
    
# desk manage
async def desk_manager(this_desk_info):
    global desk_info
    global players_info_by_name
    global global_msgs
    
    def key_power_of_hand_of_a_player(a_player_info):
        return a_player_info.key_hand_power
    
    
    def clip(min_num,num,max_num):
        if(num <= min_num):
            return min_num
        if(num >= max_num):
            return max_num
        return num
    
    
    async def end_of_a_round(this_desk_info):
        #desk基本设置
        this_desk_info.all_done_and_wait_for_next_round = False
        this_desk_info.highest_bet = 0

        #更新各个还在的玩家的 investment
        for i in range(0,MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] != None and not this_desk_info.seats[i].has_fold):
                this_desk_info.seats[i].player_investment = this_desk_info.seats[i].player_investment + this_desk_info.seats[i].player_bet
        
        #计算各个玩家底池权益，从当轮bet最少的玩家开始算
        side_equity = 0
        while True:
            player_left_num_for_equity = 0
            min_bet_player_info = None
            for i in range(0,MAX_PLAYER_ON_TABLE):
                if(this_desk_info.seats[i] != None and this_desk_info.seats[i].player_bet != 0):
                    player_left_num_for_equity = player_left_num_for_equity + 1
                    if(min_bet_player_info == None or this_desk_info.seats[i].player_bet < min_bet_player_info.player_bet):
                        min_bet_player_info = this_desk_info.seats[i]
            if(min_bet_player_info != None):
                if(not min_bet_player_info.has_fold):
                    min_bet_player_info.player_equity = min_bet_player_info.player_equity + min_bet_player_info.player_bet * player_left_num_for_equity + side_equity
                    logger.info('玩家 {} 当前底池权益:{}'.format(min_bet_player_info.player_name,min_bet_player_info.player_equity))
                side_equity = side_equity + min_bet_player_info.player_bet
                min_bet_player_info.player_bet = 0
            else:
                break

        #检查是否仅剩一个玩家没弃牌,是的话则结算
        num_of_players_not_fold = 0
        the_left_player_info = None
        for i in range(0,MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] != None and not this_desk_info.seats[i].has_fold):
                the_left_player_info = this_desk_info.seats[i]
                num_of_players_not_fold = num_of_players_not_fold + 1
        if(num_of_players_not_fold == 1):
            create_a_message("📢系统", '仅剩下玩家 {} ,赢得全部底池 {}'.format(the_left_player_info.player_name,this_desk_info.pot))
            the_left_player_info.player_chips = the_left_player_info.player_chips + the_left_player_info.player_equity
            the_left_player_info.player_floating_surplus = the_left_player_info.player_floating_surplus + the_left_player_info.player_equity - the_left_player_info.player_investment
            this_desk_info.desk_state = DESK_STATES.WAIT_TO_START
            save_persist_data()
            return

        #检查是否已在河牌阶段，是的话翻牌比大小
        if(this_desk_info.desk_state == DESK_STATES.RIVER):
            create_a_message("📢系统", '开始结算本局',do_toast = False)
            desk_cards_str = []
            for i in range(0,5):
                desk_cards_str.append(get_card_name(this_desk_info.desk_cards[i]))
            create_a_message("📢系统", '桌牌:{}'.format(str(desk_cards_str)),do_toast = False)
            create_a_message("📢系统", '底池:{}'.format(str(this_desk_info.pot)),do_toast = False)
            #计算各场上玩家牌力
            for i in range(0, MAX_PLAYER_ON_TABLE):
                if(this_desk_info.seats[i] != None and not this_desk_info.seats[i].has_fold):
                    this_desk_info.seats[i].key_hand_power = key_hand_power(get_hand_power(this_desk_info.desk_cards + this_desk_info.seats[i].hand_cards))
            #从强至弱输出玩家手牌和得到的pot
            left_players_num = num_of_players_not_fold
            while(left_players_num > 0):
                max_power_players = []
                for i in range(0, MAX_PLAYER_ON_TABLE):
                    if(this_desk_info.seats[i] != None and not this_desk_info.seats[i].has_fold):
                        if(len(max_power_players) == 0 or this_desk_info.seats[i].key_hand_power > max_power_players[0].key_hand_power):
                            max_power_players = [this_desk_info.seats[i]]
                        elif(this_desk_info.seats[i].key_hand_power == max_power_players[0].key_hand_power):
                            max_power_players.append(this_desk_info.seats[i])
                left_players_num = left_players_num - len(max_power_players)
                #相同power玩家内部按equity从高到底分pot
                max_power_players.sort(key = key_power_of_hand_of_a_player)
                for i in range(0,len(max_power_players)):
                    this_equity = max_power_players[i].player_equity
                    this_share = clip(0,this_equity,this_desk_info.pot) // (len(max_power_players)-i)
                    for i2 in range(i,len(max_power_players)):
                        this_desk_info.pot = this_desk_info.pot - this_share
                        max_power_players[i2].player_equity_final = max_power_players[i2].player_equity_final + this_share
                    #所有玩家的equity中去除此边池
                    for i2 in range(0, MAX_PLAYER_ON_TABLE):
                        if(this_desk_info.seats[i2] != None and not this_desk_info.seats[i2].has_fold):
                            this_desk_info.seats[i2].player_equity = this_desk_info.seats[i2].player_equity - this_equity
                #去掉这些已经分过share的玩家
                for player in max_power_players:
                    create_a_message("📢系统", '{} 手牌: {} {},总计投入 {} ,分取底池 {}'.format(
                        player.player_name,
                        get_card_name(player.hand_cards[0]),
                        get_card_name(player.hand_cards[1]),
                        player.player_investment,
                        player.player_equity_final
                    ),do_toast = False)
                    player.player_chips = player.player_chips + player.player_equity_final
                    player.player_floating_surplus = player.player_floating_surplus + player.player_equity_final - player.player_investment
                    #从桌上移除
                    player.has_fold = True
            this_desk_info.desk_state = DESK_STATES.WAIT_TO_START
            save_persist_data()
            return

        #进入下一轮
        if(this_desk_info.desk_state in [DESK_STATES.PREFLOP,DESK_STATES.FLOP,DESK_STATES.TURN]):
            #初始化新一轮的玩家信息
            for i in range(0, MAX_PLAYER_ON_TABLE):
                if(this_desk_info.seats[i] != None):
                    this_desk_info.seats[i].player_bet = 0
                    this_desk_info.seats[i].do_raise = False
                    this_desk_info.seats[i].in_deciding = False
                    this_desk_info.seats[i].refresh_input(INPUT_STATES.INPUT_WAIT_OTHERS)
            #翻牌
            if(this_desk_info.desk_state == DESK_STATES.PREFLOP):
                create_a_message("📢系统", '翻牌 {},{},{}'.format(
                    get_card_name(this_desk_info.desk_cards[0]),
                    get_card_name(this_desk_info.desk_cards[1]),
                    get_card_name(this_desk_info.desk_cards[2])))
                this_desk_info.desk_state = DESK_STATES.FLOP
            elif(this_desk_info.desk_state == DESK_STATES.FLOP):
                create_a_message("📢系统", '转牌 {}'.format(
                    get_card_name(this_desk_info.desk_cards[3])))
                this_desk_info.desk_state = DESK_STATES.TURN
            elif(this_desk_info.desk_state == DESK_STATES.TURN):
                create_a_message("📢系统", '河牌 {}'.format(
                    get_card_name(this_desk_info.desk_cards[4])))
                this_desk_info.desk_state = DESK_STATES.RIVER
                
            this_desk_info.refresh_table()
            #检查还能决策的人数量是否小于等于1，是的话则无需等待决策了
            num_of_players_can_act = 0
            for i in range(0, MAX_PLAYER_ON_TABLE):
                if(this_desk_info.seats[i] != None and not this_desk_info.seats[i].has_fold and this_desk_info.seats[i].player_chips > 0):
                    num_of_players_can_act = num_of_players_can_act + 1
            if(num_of_players_can_act <= 1):
                create_a_message("📢系统", '此轮无需决策，3秒后继续发牌..')
                #等待三秒再发下一张牌
#                 await asyncio.sleep(3)
                this_desk_info.start_waiting_time = datetime.now()
                this_desk_info.waiting_seconds = 3
                this_desk_info.all_done_and_wait_for_next_round = True
                return
                    
            #由小盲开始决策
            this_desk_info.wait_index = this_desk_info.SB_index
            while True:
                if(this_desk_info.seats[this_desk_info.wait_index] != None and not this_desk_info.seats[this_desk_info.wait_index].has_fold and this_desk_info.seats[this_desk_info.wait_index].player_chips > 0):
                    create_a_message("📢系统", '轮到 {} 决策了'.format(this_desk_info.seats[this_desk_info.wait_index].player_name))
                    this_desk_info.seats[this_desk_info.wait_index].refresh_input(INPUT_STATES.INPUT_OPEN)
                    this_desk_info.seats[this_desk_info.UTG_index].setting_bet = 0
                    this_desk_info.seats[this_desk_info.UTG_index].in_deciding = True
                    this_desk_info.end_index = this_desk_info.SB_index
                    break
    #统计桌上在线人数，同时去除桌上不在线的玩家
    def num_of_player_online_in_seat(this_desk_info):
        num_of_player_online_in_seat = 0
        for i in range(0, MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] != None):
                if(this_desk_info.seats[i].online):
                    num_of_player_online_in_seat = num_of_player_online_in_seat + 1
                else:
                    this_desk_info.refresh_table()
                    this_desk_info.seats[i].sit_at = -1
                    this_desk_info.seats[i] = None
        return num_of_player_online_in_seat

    while True:
        await asyncio.sleep(0.2)
        if(this_desk_info.desk_state == DESK_STATES.NOT_CREATED):
            this_desk_info.desk_state = DESK_STATES.WAIT_TO_START
        
        elif(this_desk_info.desk_state == DESK_STATES.WAIT_TO_START):
            if(num_of_player_online_in_seat(this_desk_info) >= MIN_PLAYER_TO_START):
                create_a_message("📢系统", '人数足够，5秒后开始新的一局...')
                this_desk_info.desk_state = DESK_STATES.WAIT_TO_START_WAITING
                this_desk_info.start_waiting_time = datetime.now()
                this_desk_info.waiting_seconds = 5
                continue
        
        elif(this_desk_info.desk_state == DESK_STATES.WAIT_TO_START_WAITING):
            if((datetime.now() - this_desk_info.start_waiting_time).seconds < this_desk_info.waiting_seconds):
                continue
            if(num_of_player_online_in_seat(this_desk_info) < MIN_PLAYER_TO_START):
                create_a_message("📢系统", '人数不足，重新等待...')
                this_desk_info.desk_state = DESK_STATES.WAIT_TO_START
                continue
            create_a_message("📢系统", '初始化桌面信息...')
            #初始化桌面基本信息
            this_desk_info.desk_state = DESK_STATES.PREFLOP
            this_desk_info.desk_cards = []
            this_desk_info.highest_bet = BB_BET
            this_desk_info.pot = BB_BET + SB_BET
            this_desk_info.all_done_and_wait_for_next_round = False
            #初始化桌上玩家信息
            for i in range(0, MAX_PLAYER_ON_TABLE):
                if(this_desk_info.seats[i] != None):
                    this_desk_info.seats[i].player_investment = 0
                    this_desk_info.seats[i].player_equity = 0
                    this_desk_info.seats[i].player_equity_final = 0
                    this_desk_info.seats[i].has_fold = False
                    this_desk_info.seats[i].player_bet = 0
                    this_desk_info.seats[i].sit_as = ""
                    this_desk_info.seats[i].do_raise = False
                    this_desk_info.seats[i].in_deciding = False
                    this_desk_info.seats[i].hand_cards = []
                    this_desk_info.seats[i].refresh_input(INPUT_STATES.INPUT_WAIT_OTHERS)
                    if(this_desk_info.seats[i].player_chips < AUTO_RELOAD_CHIPS_WHEN_LESS_THAN):
                        this_desk_info.seats[i].player_chips = this_desk_info.seats[i].player_chips + DEFAULT_BUYIN
            #初始化BTN位置
            while True:
                this_desk_info.BTN_index = (this_desk_info.BTN_index + 1)%MAX_PLAYER_ON_TABLE
                if(this_desk_info.seats[this_desk_info.BTN_index] != None):
                    this_desk_info.seats[this_desk_info.BTN_index].sit_as = "BTN"
                    logger.debug('BTN_index:{}'.format(this_desk_info.BTN_index))
                    break
            #初始化小盲位置
            this_desk_info.SB_index = this_desk_info.BTN_index
            while True:
                this_desk_info.SB_index = (this_desk_info.SB_index + 1)%MAX_PLAYER_ON_TABLE
                if(this_desk_info.seats[this_desk_info.SB_index] != None):
                    this_desk_info.seats[this_desk_info.SB_index].player_bet = SB_BET
                    this_desk_info.seats[this_desk_info.SB_index].player_chips = this_desk_info.seats[this_desk_info.SB_index].player_chips - SB_BET
#                         this_desk_info.seats[this_desk_info.SB_index].player_investment = SB_BET
                    this_desk_info.seats[this_desk_info.SB_index].sit_as = "SB"
                    logger.debug('SB_index:{}'.format(this_desk_info.SB_index))
                    break
            #初始化大盲位置
            this_desk_info.BB_index = this_desk_info.SB_index
            while True:
                this_desk_info.BB_index = (this_desk_info.BB_index + 1)%MAX_PLAYER_ON_TABLE
                if(this_desk_info.seats[this_desk_info.BB_index] != None):
                    this_desk_info.seats[this_desk_info.BB_index].player_bet = BB_BET
                    this_desk_info.seats[this_desk_info.BB_index].player_chips = this_desk_info.seats[this_desk_info.BB_index].player_chips - BB_BET
#                         this_desk_info.seats[this_desk_info.BB_index].player_investment = BB_BET
                    if(this_desk_info.seats[this_desk_info.BB_index].sit_as == ""):
                        this_desk_info.seats[this_desk_info.BB_index].sit_as = "BB"
                    logger.debug('BB_index:{}'.format(this_desk_info.BB_index))
                    break
            #初始化枪口位置
            this_desk_info.UTG_index = this_desk_info.BB_index
            while True:
                this_desk_info.UTG_index = (this_desk_info.UTG_index + 1)%MAX_PLAYER_ON_TABLE
                if(this_desk_info.seats[this_desk_info.UTG_index] != None):
                    if(this_desk_info.seats[this_desk_info.UTG_index].sit_as == ""):
                        this_desk_info.seats[this_desk_info.UTG_index].sit_as = "UTG"
                    this_desk_info.wait_index = this_desk_info.UTG_index
                    this_desk_info.seats[this_desk_info.UTG_index].refresh_input(INPUT_STATES.INPUT_OPEN)
                    this_desk_info.seats[this_desk_info.UTG_index].setting_bet = BB_BET - this_desk_info.seats[this_desk_info.UTG_index].player_bet
                    this_desk_info.seats[this_desk_info.UTG_index].in_deciding = True
                    this_desk_info.end_index = this_desk_info.UTG_index
                    logger.debug('UTG_index:{}'.format(this_desk_info.UTG_index))
                    break
            #随机发牌
            logger.info('玩家信息初始化完成，准备发牌')
            RandomDeal(this_desk_info)

            this_desk_info.refresh_table()
            create_a_message("📢系统", '开始新的一局,牌已发完，等待 {} Open'.format(this_desk_info.seats[this_desk_info.UTG_index].player_name))
            logger.info('开始新的一局,牌已发完，等待 {} Open'.format(this_desk_info.seats[this_desk_info.UTG_index].player_name))

        elif(this_desk_info.desk_state in [DESK_STATES.PREFLOP,DESK_STATES.FLOP,DESK_STATES.TURN,DESK_STATES.RIVER]):
            if(not this_desk_info.all_done_and_wait_for_next_round):
                continue
            if((datetime.now() - this_desk_info.start_waiting_time).seconds < this_desk_info.waiting_seconds):
                continue
            await end_of_a_round(this_desk_info)

            
            
# input manage
class INPUT_STATES:
    INPUT_CODE = 10
    INPUT_NAME  = 20
    INPUT_STAND = 30
    INPUT_WAIT_OPEN = 40
    INPUT_OPEN = 50
    INPUT_CALL = 50
    INPUT_NONE = 60
    INPUT_WAIT_OTHERS = 70

async def input_manager_once(this_player_info,this_desk_info):
    global players_info_by_name
    global global_msgs

    def try_set_a_bet(try_bet,this_player_info,this_desk_info):
        logger.debug('try_set_a_bet:try_bet:{},highest_bet:{},player_chips:{},player_bet:{}'.format(
            try_bet,this_desk_info.highest_bet,this_player_info.player_chips,this_player_info.player_bet))
        #押注过少
        result = try_bet
        if(result + this_player_info.player_bet < this_desk_info.highest_bet):
            result = this_desk_info.highest_bet - this_player_info.player_bet
        #押注过多
        if(result > this_player_info.player_chips):
            result = this_player_info.player_chips
        return result
        
        
    if(this_player_info.input_state == INPUT_STATES.INPUT_STAND):
        with use_scope('input-area', clear=True):
            input_data = await input_group("你正站在桌边观战",[
                input('聊个天:', name = 'chat_text', value = this_player_info.unsend_chat_text),
                actions(name = 'CMD', buttons = [{'label': '发送', 'value': '发送', 'color': 'warning'},
                                                 {'label': '坐下', 'value': '坐下', 'color': 'warning'},
                                                 {'label': '增加{}筹码'.format(DEFAULT_BUYIN), 'value': '增加{}筹码'.format(DEFAULT_BUYIN), 'color': 'warning'},
                                                 {'label': '减少{}筹码'.format(DEFAULT_BUYIN), 'value': '减少{}筹码'.format(DEFAULT_BUYIN), 'color': 'warning'}
                                                ])
            ])

    elif(this_player_info.input_state == INPUT_STATES.INPUT_WAIT_OPEN):
        with use_scope('input-area', clear=True):
            input_data = await input_group("等待开始新的一局",[
                input('聊个天:', name = 'chat_text', value = this_player_info.unsend_chat_text),
                actions(name = 'CMD', buttons = [{'label': '发送', 'value': '发送', 'color': 'warning'},
                                                 {'label': '站起', 'value': '坐下', 'color': 'warning'},
                                                 {'label': '增加{}筹码'.format(DEFAULT_BUYIN), 'value': '增加{}筹码'.format(DEFAULT_BUYIN), 'color': 'warning'},
                                                 {'label': '减少{}筹码'.format(DEFAULT_BUYIN), 'value': '减少{}筹码'.format(DEFAULT_BUYIN), 'color': 'warning'}])
            ])
            
    elif(this_player_info.input_state == INPUT_STATES.INPUT_OPEN):
        btn_list = ['1/3POT','1/2POT','3/4POT','POT','ALL-IN','Double','Half',
                     {'label': '确认下注', 'value': '确认下注', 'color': 'warning'},
                     {'label': '弃牌', 'value': '弃牌', 'color': 'warning'}
                   ]
        if(this_desk_info.highest_bet == this_player_info.player_bet):
            btn_list.append({'label': '过牌', 'value': '过牌', 'color': 'warning'})
        else:
            btn_list.append({'label': '跟注', 'value': '跟注', 'color': 'warning'})
        with use_scope('input-area', clear=True):
            input_data = await input_group("该你决策了",[
                input('设置下注金额:', name = 'bet_text', type=NUMBER, value = this_player_info.setting_bet),
                actions(name = 'CMD', buttons = btn_list)
            ])
            
    elif(this_player_info.input_state == INPUT_STATES.INPUT_WAIT_OTHERS):
        with use_scope('input-area', clear=True):
            if(this_desk_info.seats[this_desk_info.wait_index] != None):
                title_str = "等待 {} 操作...".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
            else:
                title_str = "等待系统操作...".format(this_desk_info.seats[this_desk_info.wait_index].player_name)
            input_data = await input_group(title_str,[
                input('聊个天:', name = 'chat_text', value = this_player_info.unsend_chat_text),
                actions(name = 'CMD', buttons = [{'label': '发送', 'value': '发送', 'color': 'warning'}])
            ])
    
    def confirm_bet(this_player_info,confirm_bet):
        this_player_info.refresh_input(INPUT_STATES.INPUT_WAIT_OTHERS)
        this_player_info.player_bet = confirm_bet + this_player_info.player_bet
        this_player_info.player_chips = this_player_info.player_chips - confirm_bet
        this_desk_info.pot = this_desk_info.pot + confirm_bet
        if(this_player_info.player_bet > this_desk_info.highest_bet):
            this_desk_info.highest_bet = this_player_info.player_bet
            this_player_info.do_raise = True
            this_desk_info.end_index = this_player_info.sit_at
        else:
            this_player_info.do_raise = False
        logger.debug('玩家 {} 下注:{}，玩家总下注{}，剩余筹码{}'.format(this_player_info.player_name,confirm_bet,this_player_info.player_bet,this_player_info.player_chips))
        if(confirm_bet == 0):
            create_a_message("📢系统", '{} 过牌'.format(this_player_info.player_name))
        else:
            create_a_message("📢系统", '{} 下注共 {}'.format(this_player_info.player_name,this_player_info.player_bet))
        
    def set_next_player(this_desk_info):
        #设置下一个操作的玩家
        this_desk_info.refresh_table()
        this_desk_info.seats[this_desk_info.wait_index].in_deciding = False
        #如果当前全场除一名玩家外都fold或allin了，则直接下一轮
        num_of_player_has_chip_and_not_fold = 0
        for i in range(0, MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] != None and not this_desk_info.seats[i].has_fold and this_desk_info.seats[i].player_chips > 0):
                num_of_player_has_chip_and_not_fold = num_of_player_has_chip_and_not_fold + 1
        if(num_of_player_has_chip_and_not_fold <= 1):
            logger.info('此轮没有需要操作的玩家了 type1')
            this_desk_info.all_done_and_wait_for_next_round = True
            return "success,no operator this round"
        
        #继续操作
        while True:
            this_desk_info.wait_index = (this_desk_info.wait_index + 1)%MAX_PLAYER_ON_TABLE
            if(this_desk_info.wait_index == this_desk_info.end_index):#没有需要操作的玩家了
                logger.info('此轮没有需要操作的玩家了 type2')
                this_desk_info.all_done_and_wait_for_next_round = True
                return "success,no operator this round"
            if(this_desk_info.seats[this_desk_info.wait_index] != None):
                next_player_info = this_desk_info.seats[this_desk_info.wait_index]
                if(not next_player_info.has_fold and next_player_info.player_chips > 0):
                    logger.debug('转换为等待玩家 {} 决策'.format(next_player_info.player_name))
                    next_player_info.refresh_input(INPUT_STATES.INPUT_OPEN)
                    next_player_info.setting_bet = try_set_a_bet(0,next_player_info,this_desk_info)
                    next_player_info.in_deciding = True
                    logger.info('等待玩家 {} 决策'.format(next_player_info.player_name))
                    return "success,wait next"
            
    
    if(input_data['CMD'] == '1/3POT'):
        this_player_info.setting_bet = try_set_a_bet(this_desk_info.pot * 1 // 3,this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == '1/2POT'):
        this_player_info.setting_bet = try_set_a_bet(this_desk_info.pot * 1 // 2,this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == '3/4POT'):
        this_player_info.setting_bet = try_set_a_bet(this_desk_info.pot * 3 // 4,this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == 'POT'):
        this_player_info.setting_bet = try_set_a_bet(this_desk_info.pot,this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == 'ALL-IN'):
        this_player_info.setting_bet = try_set_a_bet(this_player_info.player_chips,this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == 'Double'):
        this_player_info.setting_bet = try_set_a_bet(int(input_data['bet_text']*2),this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == 'Half'):
        this_player_info.setting_bet = try_set_a_bet(int(input_data['bet_text']//2),this_player_info,this_desk_info)
        this_player_info.refresh_input()
        
    elif(input_data['CMD'] == '确认下注'):
        bet_before = int(input_data['bet_text'])
        bet_after = try_set_a_bet(bet_before,this_player_info,this_desk_info)
        if(bet_before == bet_after):#合法成功下注
            confirm_bet(this_player_info,bet_after)
            set_next_player(this_desk_info)
        else:
            toast('下注金额已自动修改为{},点[确认下注]下注'.format(bet_after))
            this_player_info.setting_bet = bet_after
        this_player_info.refresh_input()
            
    elif(input_data['CMD'] == '过牌'):
        if(this_desk_info.highest_bet == this_player_info.player_bet):
            confirm_bet(this_player_info,0)
            set_next_player(this_desk_info)
        else:
            toast('不可过牌')
        this_player_info.refresh_input()
            
    elif(input_data['CMD'] == '跟注'):
        confirm_bet(this_player_info, this_desk_info.highest_bet - this_player_info.player_bet)
        set_next_player(this_desk_info)
        this_player_info.refresh_input()
    
    elif(input_data['CMD'] == '弃牌'):
        create_a_message("📢系统", '{} 弃牌'.format(this_player_info.player_name))
        this_player_info.has_fold = True
        this_player_info.player_floating_surplus = this_player_info.player_floating_surplus - this_player_info.player_investment - this_player_info.player_bet
        this_player_info.refresh_input(INPUT_STATES.INPUT_WAIT_OPEN)
        set_next_player(this_desk_info)
        
    elif(input_data['CMD'] == '发送'):
        create_a_message('{}'.format(this_player_info.player_name), '{}'.format(input_data['chat_text']))
        this_player_info.refresh_input()
        last_chat_text = ""

    elif(input_data['CMD'] == '坐下'):
        have_seat = False
        for i in range(0, MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] == None):
                have_seat = True
                this_desk_info.seats[i] = this_player_info
                this_player_info.has_fold = True
                this_player_info.sit_at = i
                create_a_message("📢系统", '{} 坐下了'.format(this_player_info.player_name))
                if(this_desk_info.desk_state == DESK_STATES.NOT_CREATED and this_desk_info.num_of_player_in_seat() < MIN_PLAYER_TO_START):
                    create_a_message("📢系统", '当前坐下共 {} 人，达到 {} 人后将自动开始发牌'.format(this_desk_info.num_of_player_in_seat(),MIN_PLAYER_TO_START),do_toast= False)
                this_desk_info.refresh_table()
                this_player_info.refresh_input(INPUT_STATES.INPUT_WAIT_OPEN)
                this_player_info.unsend_chat_text = input_data['chat_text']
                break
        if(not have_seat):
            toast("当前没有座位")
        this_player_info.refresh_input()

    elif(input_data['CMD'] == '站起'):
        this_player_info.refresh_input(INPUT_STATES.INPUT_STAND)
        for i in range(0, MAX_PLAYER_ON_TABLE):
            if(this_desk_info.seats[i] == this_player_info):
                this_desk_info.seats[i] = None
                this_player_info.sit_at = -1
                create_a_message("📢系统", '{} 站起来了'.format(this_player_info.player_name))
                this_desk_info.refresh_table()
                this_player_info.unsend_chat_text = input_data['chat_text']
                break
        this_player_info.refresh_input()

    elif(input_data['CMD'] == '增加{}筹码'.format(DEFAULT_BUYIN)):
        this_player_info.player_chips = this_player_info.player_chips + DEFAULT_BUYIN
        create_a_message("📢系统", '玩家 {} 调整手上筹码至 {}'.format(this_player_info.player_name,this_player_info.player_chips))
        this_desk_info.refresh_table()
        this_player_info.unsend_chat_text = input_data['chat_text']
        this_player_info.refresh_input()

    elif(input_data['CMD'] == '减少{}筹码'.format(DEFAULT_BUYIN)):
        if(this_player_info.player_chips > DEFAULT_BUYIN + AUTO_RELOAD_CHIPS_WHEN_LESS_THAN):
            this_player_info.player_chips = this_player_info.player_chips - DEFAULT_BUYIN
            create_a_message("📢系统", '玩家 {} 调整手上筹码至 {}'.format(this_player_info.player_name,this_player_info.player_chips))
            this_desk_info.refresh_table()
            this_player_info.unsend_chat_text = input_data['chat_text']
        else:
            toast('无法减少，已仅剩 {} 筹码'.format(this_player_info.player_chips))
        this_player_info.refresh_input()

async def input_manager(this_player_info):
    global desk_info
    global players_info_by_name
    global global_msgs

    current_input_version = -1
    input_manager_once_task = None

    while True:
        await asyncio.sleep(0.2)
        if(this_player_info.input_version != current_input_version):# INPUT_version changes
            this_player_info.input_version = current_input_version
            if(input_manager_once_task != None):
                logger.debug('input_manager_once_task.close()')
                try:
                    input_manager_once_task.cancel()
                    input_manager_once_task.close()
                except:
                    logger.debug('input_manager_once_task.close() exception')
            input_manager_once_task = run_async(input_manager_once(this_player_info,desk_info))


# server_main
free_session_id = 0

async def main():
    
    global desk_info
    global players_info_by_name
    global global_msgs
    global free_session_id
    session_id = free_session_id
    free_session_id = free_session_id +1
    logger.info('session {} created'.format(session_id))
    
    for v in players_info_by_name.values():
        logger.info("所有玩家信息：{}".format(str(v)))
    
    basic_layout()
    this_player_info = await player_login()
    
    player_join(this_player_info)
    
    with use_scope('head-area', clear=True):
        put_markdown("## Poker Online\n随便玩玩")
    
    with use_scope('msg-area', clear=True):
        put_scrollable(put_scope('msg-box'), height=300, keep_bottom=True)
        
    @defer_call
    def on_close():
        logger.info('session {} closed'.format(session_id))
        player_leave(this_player_info)
        
    async_task1 = run_async(desk_manager(desk_info))
    async_task3 = run_async(info_table_manager(this_player_info,desk_info))  
    async_task4 = run_async(msg_manager(this_player_info))  
    
    await input_manager(this_player_info)
    
    ##Finish
    async_task1.cancel()
    async_task2.cancel()
    async_task3.cancel()
    toast("你离开了房间")
    
    
    
# run
load_persist_data()
config(title='核心')
start_server(main, debug = True, port = 8894)