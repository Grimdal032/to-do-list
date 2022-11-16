from nanoid import generate
from flask import Flask, render_template, request, jsonify
app = Flask(__name__)

from pymongo import MongoClient
import certifi
ca = certifi.where()
client = MongoClient('mongodb+srv://test:sparta@cluster0.q6bdrv2.mongodb.net/Cluster0?retryWrites=true&w=majority', tlsCAFile=ca)
db = client.dbsparta

# JWT 토큰을 만들 때 필요한 비밀문자열입니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'SPARTA'

# JWT 패키지를 사용합니다.
import jwt

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# 회원가입 시에, 비밀번호를 암호화하여 db에 저장
import hashlib



@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        return render_template('index.html', id=user_info["id"], nickname=user_info["nick"])
    except jwt.ExpiredSignatureError:
        return render_template('index.html', msg="로그인 시간이 만료되었습니다.")
    except jwt.exceptions.DecodeError:
        return render_template('index.html', msg="로그인 정보가 존재하지 않습니다.")

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')


# to-do 관련 함수
@app.route("/todo_post", methods=["POST"])
def todo_post():
    list_receive = request.form['list_give']
    year = request.form['year_give']
    month = request.form['month_give']
    day = request.form['day_give']
    id = request.form['id_give']

    count = generate()

    doc = {
        'list': list_receive,
        'year': year,
        'month': month,
        'day': day,
        'num': count,
        'done': 0,
        'id': id
    }
    db.lists.insert_one(doc)
    return jsonify({'msg': '등록 완료!'})

@app.route("/todo_show", methods=["GET"])
def todo_get():
    lists = list(db.lists.find({}, {'_id': False}))
    return jsonify({'lists': lists})

@app.route("/todo_done", methods=["POST"])
def todo_done():
    num_receive = request.form['num_give']
    db.lists.update_one({'num': num_receive}, {'$set': {'done': 1}})
    return jsonify({'msg': '버킷 완료!'})

@app.route("/todo_undone", methods=["POST"])
def todo_undone():
    num_receive = request.form['num_give']
    db.lists.update_one({'num': num_receive}, {'$set': {'done': 0}})
    return jsonify({'msg': '버킷 취소!'})

@app.route("/todo_priority", methods=["POST"])
def todo_priority():
    num_receive = request.form['num_give']
    db.lists.update_one({'num': num_receive}, {'$set': {'priority': 1}})
    return jsonify({'msg': '버킷 완료!'})

@app.route("/todo_nopriority", methods=["POST"])
def todo_nopriority():
    num_receive = request.form['num_give']
    db.lists.update_one({'num': num_receive}, {'$set': {'priority': 0}})
    return jsonify({'msg': '버킷 완료!'})

@app.route("/todo_delete", methods=["POST"])
def todo_delete():
    num_receive = request.form['num_give']
    db.lists.delete_one({'num': num_receive})
    return jsonify({'msg': '버킷 삭제!'})

#################################
##  로그인을 위한 API            ##
#################################

# [회원가입 API]
# id, pw, nickname을 받아서, mongoDB에 저장합니다.
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route('/api/register', methods=['POST'])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']
    nickname_receive = request.form['nickname_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    db.user.insert_one({'id': id_receive, 'pw': pw_hash, 'nick': nickname_receive})

    return jsonify({'result': 'success'})

# [중복확인 API]
@app.route('/api/idcheck', methods=['POST'])
def idcheck():

    id_receive = request.form['id_give']
    result = db.user.find_one({'id': id_receive})
    if result is None:
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'fail'})

@app.route('/api/nickcheck', methods=['POST'])
def nickcheck():

    nick_receive = request.form['nick_give']
    result = db.user.find_one({'nick': nick_receive})
    if result is None:
        return jsonify({'result': 'success'})
    else:
        return jsonify({'result': 'fail'})


# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()
    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})
    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=6000)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)