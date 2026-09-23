import re
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from openai import OpenAI
import stripe
import os
client = OpenAI()

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")
app = Flask(__name__)
app.secret_key = "careerhero-secret-key"

def get_db():
    conn = sqlite3.connect("careerhero.db")
    conn.row_factory = sqlite3.Row
    return conn
def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    create_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    try:
        conn.execute("""
            ALTER TABLE users
            ADD COLUMN is_pro INTEGER DEFAULT 0
        """)
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS self_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            question1 TEXT,
            question2 TEXT,
            question3 TEXT,
            question4 TEXT,
            question5 TEXT,
            question6 TEXT,
            question7 TEXT,
            question8 TEXT,
            question9 TEXT,
            question10 TEXT,
            question11 TEXT,
            question12 TEXT,
            question13 TEXT,
            question14 TEXT,
            question15 TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS ai_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS es_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            question TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
     CREATE TABLE IF NOT EXISTS es_review_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            question TEXT NOT NULL,
            es_text TEXT NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_name TEXT NOT NULL,
            status TEXT DEFAULT '未応募',
            deadline TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
         CREATE TABLE IF NOT EXISTS gakuchika_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            experience TEXT NOT NULL,
            challenge TEXT NOT NULL,
            action TEXT NOT NULL,
            result TEXT NOT NULL,
            learning TEXT NOT NULL,
            max_length INTEGER NOT NULL,
            generated_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
    )

    """)

    try:
        conn.execute("""
        ALTER TABLE companies
        ADD COLUMN memo TEXT
    """)
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            ALTER TABLE es_history
            ADD COLUMN company_id INTEGER
        """)
    except sqlite3.OperationalError:
        pass

    try:
        conn.execute("""
            ALTER TABLE gakuchika_history
            ADD COLUMN company_id INTEGER
        """)
    except sqlite3.OperationalError:
        pass


    conn.execute("""
        CREATE TABLE IF NOT EXISTS mock_interview_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS mock_interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            evaluation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS company_analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            result TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (company_id) REFERENCES companies(id)
        )
    """)
    try:
        conn.execute("""
            ALTER TABLE mock_interview_history
            ADD COLUMN session_id INTEGER
        """)
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()
    
init_db()

@app.route("/regiater",methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor()
    # ユーザー名は3～20文字
        if len(username) < 3 or len(username) > 20:
            flash("ユーザー名は3〜20文字で入力してください")
            conn.close()
            return redirect(url_for("register"))

# ユーザー名は英数字と_のみ
        if not re.fullmatch(r"[A-Za-z0-9_]+", username):
            flash("ユーザー名は英数字と_のみ使用できます")
            conn.close()
            return redirect(url_for("register"))

# ユーザー名とパスワードは同じにできない
        if username == password:
            flash("ユーザー名とパスワードは同じにできません")
            conn.close()
            return redirect(url_for("register"))

# パスワードは8文字以上
        if len(password) < 8:
            flash("パスワードは8文字以上にしてください")
            conn.close()
            return redirect(url_for("register"))

# 英字を含む
        if not re.search(r"[A-Za-z]", password):
            flash("パスワードには英字を含めてください")
            conn.close()
            return redirect(url_for("register"))

# 数字を含む
        if not re.search(r"\d", password):
            flash("パスワードには数字を含めてください")
            conn.close()
            return redirect(url_for("register"))

        cursor.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        )

        if cursor.fetchone():
            flash("そのユーザー名は既に使われています")
            conn.close()
            return redirect(url_for("register"))
        
        hashed_password = generate_password_hash(password)

        cursor.execute("""
                       INSERT INTO users (username, password)
                       VALUES (?, ?)
                       """, (username, hashed_password))

        conn.commit()
        conn.close()
        flash("登録が完了しました！ログインしてください")
        return redirect(url_for("login"))
        

    return render_template("register.html")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        cursor = conn.cursor() 

        cursor.execute("""
        SELECT * FROM users
        WHERE username = ?
        """, (username,))

        user = cursor.fetchone()        

        conn.close()

        if user and check_password_hash(user["password"], password):
            session["username"] = user["username"]
            session["user_id"] = user["id"]

            flash("ログインしました")
            return redirect(url_for("dashboard"))
        else:
            flash("ユーザー名またはパスワードが違います")
        


    return render_template("login.html")
@app.route("/dashboard")
def dashboard():

    if "username" not in session:
        return redirect(url_for("login"))


    conn = get_db()

    user = conn.execute("""
        SELECT is_pro
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    companies = conn.execute("""
        SELECT status, COUNT(*) as count
        FROM companies
        WHERE user_id = ?
        GROUP BY status
    """, (session["user_id"],)).fetchall()

    upcoming_deadlines = conn.execute("""
        SELECT 
            company_name, 
            deadline, 
            status,
            CAST(julianday(deadline) - julianday(date('now')) AS INTEGER) AS days_left
        FROM companies
        WHERE user_id = ?
            AND deadline IS NOT NULL
            AND deadline != ''
            AND deadline >= date('now')
        ORDER BY deadline ASC
        LIMIT 5
    """, (session["user_id"],)).fetchall()

    conn.close()

    company_counts = {}

    for company in companies:
        company_counts[company["status"]] = company["count"]

    total_companies = sum(company_counts.values())
    es_submitted = company_counts.get("ES提出済み", 0)
    interview = company_counts.get("面接予定", 0)
    offers = company_counts.get("内定", 0)
    return render_template(
        "dashboard.html",
        total_companies=total_companies,
        es_submitted=es_submitted,
        interview=interview,
        offers=offers,
        upcoming_deadlines=upcoming_deadlines,
        is_pro=user["is_pro"])


@app.route("/self-analysis", methods=["GET", "POST"])
def self_analysis():

    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        question1 = request.form["question1"]
        question2 = request.form["question2"]
        question3 = request.form["question3"]
        question4 = request.form["question4"]
        question5 = request.form["question5"]
        question6 = request.form["question6"]
        question7 = request.form["question7"]
        question8 = request.form["question8"]
        question9 = request.form["question9"]
        question10 = request.form["question10"]
        question11 = request.form["question11"]
        question12 = request.form["question12"]
        question13 = request.form["question13"]
        question14 = request.form["question14"]
        question15 = request.form["question15"]


        conn = get_db()

        conn.execute("""
            INSERT INTO self_analysis(
                user_id,
                question1, 
                question2,
                question3, 
                question4, 
                question5,
                question6,
                question7,
                question8,
                question9,
                question10,
                question11,
                question12,
                question13,
                question14,
                question15
                )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            question1,
            question2,
            question3,
            question4,
            question5,
            question6,
            question7,
            question8,
            question9,
            question10,
            question11,
            question12,
            question13,
            question14,
            question15
        ))

        conn.commit()
        conn.close()

        flash("自己分析を保存しました！")

        return redirect(url_for("self_analysis"))

    return render_template("self_analysis.html")

@app.route("/ai-test")
def ai_test():

    response = client.responses.create(
        model="gpt-5.6-luna",
        input="こんにちは。あなたは就活をサポートするAIです。短く自己紹介してください。"
    )

    return response.output_text
@app.route("/ai-analysis", methods=["POST"])
def ai_analysis():

    if "username" not in session:
        return redirect(url_for("login"))

    # フォームから15個の回答を取得
    answers = []

    for i in range(1, 16):
        answer = request.form.get(f"question{i}", "")
        answers.append(answer)

    # AIに渡す文章
    prompt = f"""
あなたは大学生の就職活動をサポートするAIです。

以下は、ある大学生が自己分析で回答した内容です。

【自己分析回答】
1. {answers[0]}
2. {answers[1]}
3. {answers[2]}
4. {answers[3]}
5. {answers[4]}
6. {answers[5]}
7. {answers[6]}
8. {answers[7]}
9. {answers[8]}
10. {answers[9]}
11. {answers[10]}
12. {answers[11]}
13. {answers[12]}
14. {answers[13]}
15. {answers[14]}

この回答を分析して、以下の内容を日本語で分かりやすくまとめてください。

・あなたの強み
・あなたの弱み
・あなたの性格や特徴
・大切にしていそうな価値観
・向いていそうな仕事
・向いていそうな業界
・就活でアピールすると良いポイント
・今後伸ばすと良いポイント

大学生本人に直接アドバイスするような形で書いてください。
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        input=prompt
    )

    result = response.output_text

    # AI分析結果をデータベースに保存
    conn = get_db()

    conn.execute("""
        INSERT INTO ai_analysis (user_id, result)
        VALUES (?, ?)
    """, (
        session["user_id"],
        result
    ))

    conn.commit()
    conn.close()

    return render_template(
        "ai_analysis.html",
        result=result
    )
@app.route("/ai-history")
def ai_history():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    analyses = conn.execute("""
        SELECT id, result, created_at
        FROM ai_analysis
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "ai_history.html",
        analyses=analyses
    )
@app.route("/es-generator", methods=["GET", "POST"])
def es_generator():

    if "username" not in session:
        return redirect(url_for("login"))

    company_id = request.args.get("company_id")

    if request.method == "POST":

        company_id = request.form["company_id"]
        question = request.form["question"]
        max_length = request.form["max_length"]

        conn = get_db()

        company = conn.execute("""
            SELECT id, company_name
            FROM companies
            WHERE id = ? AND user_id = ?
        """, (company_id, session["user_id"])).fetchone()

        if not company:
            flash("企業が見つかりません")
            return redirect(url_for("es_generator"))

        company_name = company["company_name"]
        company = company_name

        analysis = conn.execute("""
            SELECT *
            FROM self_analysis
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (session["user_id"],)).fetchone()

        conn.close()

        if not analysis:
            flash("先に自己分析を保存してください")
            return redirect(url_for("self_analysis"))

        answers = []

        for i in range(1, 16):
            answers.append(analysis[f"question{i}"])

        prompt = f"""
あなたは大学生の就職活動をサポートするAIです。

以下の自己分析回答をもとに、企業のESを作成してください。

【企業名】
{company}

【ESの設問】
{question}

【文字数】
{max_length}文字程度

【自己分析回答】
"""

        for i, answer in enumerate(answers, 1):
            prompt += f"{i}. {answer}\n"

        prompt += f"""

上記の情報をもとに、本人の経験や考えを活かしたESを日本語で作成してください。

条件：
・{max_length}文字程度
・本人が実際に経験した内容から作る
・経験を勝手に作らない
・自然な大学生の文章にする
・企業に伝わりやすい文章にする
・ES本文だけを出力する
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result = response.output_text

        # ESをデータベースに保存
        conn = get_db()

        conn.execute("""
            INSERT INTO es_history (
                user_id,
                company,
                company_id,
                question,
                result
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            company_name,
            company_id,
            question,
            result
        ))

        conn.commit()
        conn.close()

        return render_template(
            "es_result.html",
            company=company,
            question=question,
            result=result
            )
    conn = get_db()

    companies = conn.execute("""
        SELECT id, company_name
        FROM companies
        WHERE user_id = ?
        ORDER BY company_name ASC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "es_generator.html",
        companies=companies,
        selected_company_id=company_id)
@app.route("/es-history")
def es_history():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    histories = conn.execute("""
        SELECT id, company, question, result, created_at
        FROM es_history
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "es_history.html",
        histories=histories
    )
@app.route("/delete-es/<int:es_id>", methods=["POST"])
def delete_es(es_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM es_history
        WHERE id = ? AND user_id = ?
    """, (es_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("ESを削除しました")

    return redirect(url_for("es_history"))
@app.route("/es-review", methods=["GET", "POST"])
def es_review():

    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        company = request.form["company"]
        question = request.form["question"]
        es_text = request.form["es_text"]
        max_length = request.form["max_length"]

        prompt = f"""
あなたは大学生の就職活動をサポートするAIです。

以下のESを添削してください。

【企業名】
{company}

【ESの設問】
{question}

【現在のES】
{es_text}

【目標文字数】
{max_length}文字程度

以下の形式で日本語で回答してください。

【良いところ】
現在のESの良い点を具体的に説明してください。

【改善ポイント】
企業により伝わりやすくするための改善点を説明してください。

【添削後のES】
元のESの内容や本人の経験を尊重しながら、自然で伝わりやすい文章にしてください。
経験や実績を勝手に追加しないでください。
{max_length}文字程度にしてください。

【アドバイス】
今後ESを書くときに意識すると良いポイントを簡潔に説明してください。
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result = response.output_text

        # ES添削結果をデータベースに保存
        conn = get_db()

        conn.execute("""
            INSERT INTO es_review_history (
                user_id,
                company,
                question,
                es_text,
                result
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            company,
            question,
            es_text,
            result
        ))

        conn.commit()
        conn.close()


        return render_template(
            "es_review_result.html",
            company=company,
            question=question,
            es_text=es_text,
            result=result
        )

    return render_template("es_review.html")
@app.route("/es-review-history")
def es_review_history():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    histories = conn.execute("""
        SELECT id, company, question, es_text, result, created_at
        FROM es_review_history
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "es_review_history.html",
        histories=histories
    )
@app.route("/delete-es-review/<int:review_id>", methods=["POST"])
def delete_es_review(review_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM es_review_history
        WHERE id = ? AND user_id = ?
    """, (review_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("ES添削履歴を削除しました")

    return redirect(url_for("es_review_history"))
@app.route("/companies", methods=["GET", "POST"])
def companies():

    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        company_name = request.form["company_name"]
        status = request.form["status"]
        deadline = request.form["deadline"]
        memo = request.form.get("memo", "")

        conn = get_db()

        conn.execute("""
            INSERT INTO companies (
                user_id,
                company_name,
                status,
                deadline,
                memo
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            company_name,
            status,
            deadline,
            memo
        ))

        conn.commit()
        conn.close()

        flash("企業を登録しました！")

        return redirect(url_for("companies"))

    conn = get_db()
    companies = conn.execute("""
        SELECT id, company_name, status, deadline, memo, created_at
        FROM companies
        WHERE user_id = ?
        ORDER BY deadline ASC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "companies.html",
        companies=companies
    )
@app.route("/delete-company/<int:company_id>", methods=["POST"])
def delete_company(company_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM companies
        WHERE id = ? AND user_id = ?
    """, (company_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("企業を削除しました")

    return redirect(url_for("companies"))
@app.route("/edit-company/<int:company_id>", methods=["GET", "POST"])
def edit_company(company_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    company = conn.execute("""
        SELECT id, company_name, status, deadline
        FROM companies
        WHERE id = ? AND user_id = ?
    """, (company_id, session["user_id"])).fetchone()

    if not company:
        conn.close()
        flash("企業が見つかりません")
        return redirect(url_for("companies"))

    if request.method == "POST":

        company_name = request.form["company_name"]
        status = request.form["status"]
        deadline = request.form["deadline"]
        memo = request.form.get("memo", "")

        conn.execute("""
            UPDATE companies
            SET company_name = ?,
                status = ?,
                deadline = ?,
                memo = ?
            WHERE id = ? AND user_id = ?
        """, (
            company_name,
            status,
            deadline,
            memo,
            company_id,
            session["user_id"]
        ))

        conn.commit()
        conn.close()

        flash("企業情報を更新しました！")

        return redirect(url_for("companies"))

    conn.close()

    return render_template(
        "edit_company.html",
        company=company
    )
@app.route("/gakuchika", methods=["GET", "POST"])
def gakuchika():

    if "username" not in session:
        return redirect(url_for("login"))

    company_id = request.args.get("company_id")

    conn = get_db()

    companies = conn.execute("""
        SELECT id, company_name
        FROM companies
        WHERE user_id = ?
        ORDER BY company_name ASC
    """, (session["user_id"],)).fetchall()

    conn.close()

    if request.method == "POST":

        company_id = request.form.get("company_id")

        if not company_id:
            flash("企業を選択してください。")
            return redirect(url_for("gakuchika"))


        experience = request.form["experience"]
        challenge = request.form["challenge"]
        action = request.form["action"]
        result = request.form["result"]
        learning = request.form["learning"]
        max_length = request.form["max_length"]

        prompt = f"""
あなたは大学生の就職活動をサポートするAIです。

以下の学生の経験をもとに、「学生時代に力を入れたこと（ガクチカ）」を作成してください。

【経験】
{experience}

【課題・苦労】
{challenge}

【行動・工夫】
{action}

【結果】
{result}

【学んだこと】
{learning}

【文字数】
{max_length}文字程度

条件：
・本人が実際に経験した内容だけを使う
・経験や実績を勝手に追加しない
・「経験→課題→行動→結果→学び」の流れを意識する
・自然な大学生の文章にする
・企業に伝わりやすい文章にする
・{max_length}文字程度にする
・ガクチカ本文だけを出力する
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result_text = response.output_text

        conn = get_db()

        conn.execute("""
            INSERT INTO gakuchika_history (
                user_id,
                company_id,
                experience,
                challenge,
                action,
                result,
                learning,
                max_length,
                generated_text
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            company_id,
            experience,
            challenge,
            action,
            result,
            learning,
            max_length,
            result_text
        ))

        conn.commit()
        conn.close()

        return render_template(
            "gakuchika_result.html",
            result=result_text,
            max_length=max_length
        )

    return render_template(
        "gakuchika.html",
        companies=companies,
        company_id=company_id
        )
@app.route("/gakuchika-history")
def gakuchika_history():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    histories = conn.execute("""
        SELECT
            id,
            experience,
            challenge,
            action,
            result,
            learning,
            max_length,
            generated_text,
            created_at
        FROM gakuchika_history
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "gakuchika_history.html",
        histories=histories
    )
@app.route("/delete-gakuchika/<int:history_id>", methods=["POST"])
def delete_gakuchika(history_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM gakuchika_history
        WHERE id = ? AND user_id = ?
    """, (history_id, session["user_id"]))

    conn.commit()
    conn.close()

    flash("ガクチカを削除しました")

    return redirect(url_for("gakuchika_history"))

@app.route("/company/<int:company_id>")
def company_detail(company_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    company = conn.execute("""
        SELECT *
        FROM companies
        WHERE id = ? AND user_id = ?
    """, (company_id, session["user_id"])).fetchone()

    if not company:
        conn.close()
        flash("企業が見つかりません")
        return redirect(url_for("companies"))

    es_histories = conn.execute("""
        SELECT id, question, result, created_at
        FROM es_history
        WHERE company_id = ? AND user_id = ?
        ORDER BY created_at DESC
    """, (company_id, session["user_id"])).fetchall()

    gakuchika_histories = conn.execute("""
        SELECT id, generated_text, created_at
        FROM gakuchika_history
        WHERE company_id = ? AND user_id = ?
        ORDER BY created_at DESC
    """, (company_id, session["user_id"])).fetchall()
    ai_interview_histories = conn.execute("""
        SELECT id, evaluation, created_at
        FROM mock_interview_sessions
        WHERE company_id = ? AND user_id = ?
        ORDER BY created_at DESC
    """, (
        company_id,
        session["user_id"]
    )).fetchall()
    conn.close()

    if not company:
        flash("企業が見つかりません")
        return redirect(url_for("companies"))

    return render_template(
        "company_detail.html",
        company=company,
        es_histories=es_histories,
        gakuchika_histories=gakuchika_histories,
        ai_interview_histories=ai_interview_histories
    )
@app.route("/ai-interview", methods=["GET", "POST"])
def ai_interview():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    companies = conn.execute("""
        SELECT id, company_name
        FROM companies
        WHERE user_id = ?
        ORDER BY company_name ASC
    """, (session["user_id"],)).fetchall()

    conn.close()

    if request.method == "POST" and not request.form.get("answer"):

        company_id = request.form.get("company_id")

        if not company_id:
            flash("企業を選択してください。")
            return redirect(url_for("ai_interview"))
        # 新しい面接を開始するので、前回の回答を削除
        conn = get_db()

        cursor = conn.execute("""
            INSERT INTO mock_interview_sessions(
                user_id,
                company_id
            )
            VALUES(?, ?)
        """,(
            session["user_id"],
            company_id
        ))

        mock_session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        #今回の面接セッションIDを保存
        session["mock_interview_session_id"] = mock_session_id
        #選択したい企業を取得
        conn = get_db()

        company = conn.execute("""
            SELECT id, company_name
            FROM companies
            WHERE id = ? AND user_id = ?
        """, (company_id, session["user_id"])).fetchone()

        conn.close()

        if not company:
            flash("企業が見つかりません。")
            return redirect(url_for("ai_interview"))

        #AIに質問を作ってもらう
        prompt = f"""
あなたは{company['company_name']}の採用面接官です。

これから大学生の就職面接を行います。

まず最初の質問を1つだけしてください。

条件：
・本番の面接らしい自然な質問にする
・大学生向けの質問にする
・質問だけを出力する
・自己紹介から始める
"""
        response = client.responses.create(
          model="gpt-5.6-luna",
          input=prompt  
        )

        first_question = response.output_text

        return render_template(
            "ai_interview.html",
            companies=companies,
            company=company,
            question=first_question
        )

    # =========================
    # 面接の回答
    # =========================
    if request.method == "POST" and request.form.get("answer"):

        company_id = request.form.get("company_id")
        question = request.form.get("question")
        answer = request.form.get("answer")

        # 今までの回答数を取得
        conn = get_db()

        company = conn.execute("""
            SELECT id, company_name
            FROM companies
            WHERE id = ? AND user_id = ?
        """,(
            company_id,
            session["user_id"]
        )).fetchone()

        conn.close()

        if not company:
            flash("企業が見つかりません。")
            return redirect(url_for("ai_interview"))
        #面接の質問と回答を保持

        conn = get_db()

        mock_session_id = session.get("mock_interview_session_id")

        conn.execute("""
            INSERT INTO mock_interview_history(
                user_id,
                company_id,
                session_id,
                question,
                answer
            )
            VALUES(?, ?, ?, ?, ?)
        """,(
            session["user_id"],
            company_id,
            mock_session_id,
            question,
            answer
        ))

        conn.commit()
        conn.close()

        #今までの回答数を取特
        mock_session_id = session.get("mock_interview_session_id")

        conn = get_db()

        answer_count = conn.execute("""
            SELECT COUNT(*)
            FROM mock_interview_history
            WHERE user_id = ?
            AND company_id = ?
            AND session_id = ?
        """, (
            session["user_id"],
            company_id,
            mock_session_id
        )).fetchone()[0]

        conn.close()
        #5問目なら面接終了
        if answer_count >= 5:
            conn = get_db()


            histories = conn.execute("""
                SELECT question, answer
                FROM mock_interview_history
                WHERE user_id = ?
                AND company_id = ?
                AND session_id = ?
                ORDER BY created_at ASC
            """, (
                session["user_id"],
                company_id,
                mock_session_id
            )).fetchall()

            conn.close()

            interview_text = ""

            for i, history in enumerate(histories, 1):
                interview_text += f"""
【質問{i}】
{history['question']}

【回答{i}】
{history['answer']}

"""

            prompt = f"""
あなたは大学生の就職活動をサポートするAI面接官です。

以下は{company['company_name']}の面接練習の記録です。

{interview_text}

この面接について総合評価してください。

以下の形式で出力してください。

【総合評価】
面接全体について簡潔に評価してください。

【良かった点】
良かった点を具体的に書いてください。

【改善するとよい点】
改善点を具体的に書いてください。

【次回へのアドバイス】
次の面接に向けたアドバイスを書いてください。

【総合スコア】
100点満点で評価してください。
"""

            response = client.responses.create(
                model="gpt-5.6-luna",
                input=prompt
            )

            evaluation = response.output_text

            conn = get_db()

            conn.execute("""
                UPDATE mock_interview_sessions
                SET evaluation = ?
                WHERE id = ?
                AND user_id = ?
            """,(
                evaluation,
                mock_session_id,
                session["user_id"]
            ))

            conn.commit()
            conn.close()

            return render_template(
                "ai_interview.html",
                companies=companies,
                company=company,
                evaluation=evaluation,
                finished=True
            )
        # 5問目より前なら次の質問
        prompt = f"""
あなたは{company['company_name']}の採用面接官です。

現在、大学生の就職面接を行っています。

あなたがした質問：
{question}

学生の回答：
{answer}

この回答を踏まえて、次の面接質問を1つだけしてください。

条件：
・学生の回答内容に関連した質問にする
・本番の面接らしく自然にする
・大学生向けにする
・質問だけを出力する
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        next_question = response.output_text

        return render_template(
            "ai_interview.html",
            companies=companies,
            company=company,
            question=next_question
        )
    return render_template(
        "ai_interview.html",
        companies=companies
    )
@app.route("/ai-interview-history")
def ai_interview_history():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    sessions = conn.execute("""
        SELECT
            mock_interview_sessions.id,
            mock_interview_sessions.company_id,
            companies.company_name,
            mock_interview_sessions.evaluation,
            mock_interview_sessions.created_at
        FROM mock_interview_sessions
        JOIN companies
            ON mock_interview_sessions.company_id = companies.id
        WHERE mock_interview_sessions.user_id = ?
        ORDER BY mock_interview_sessions.created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "ai_interview_history.html",
        sessions=sessions
    )
@app.route("/ai-interview-history/<int:session_id>")
def ai_interview_history_detail(session_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    # 面接セッションを取得
    interview_session = conn.execute("""
        SELECT
            mock_interview_sessions.id,
            mock_interview_sessions.company_id,
            mock_interview_sessions.evaluation,
            mock_interview_sessions.created_at,
            companies.company_name
        FROM mock_interview_sessions
        JOIN companies
            ON mock_interview_sessions.company_id = companies.id
        WHERE mock_interview_sessions.id = ?
        AND mock_interview_sessions.user_id = ?
    """, (
        session_id,
        session["user_id"]
    )).fetchone()

    if not interview_session:
        conn.close()
        flash("面接履歴が見つかりません。")
        return redirect(url_for("ai_interview_history"))

    # この面接の質問・回答を取得
    histories = conn.execute("""
        SELECT
            question,
            answer,
            created_at
        FROM mock_interview_history
        WHERE session_id = ?
        AND user_id = ?
        ORDER BY created_at ASC
    """, (
        session_id,
        session["user_id"]
    )).fetchall()

    conn.close()

    return render_template(
        "ai_interview_history_detail.html",
        interview_session=interview_session,
        histories=histories
    )
@app.route("/ai-interview-history/<int:session_id>/delete", methods=["POST"])
def delete_ai_interview_history(session_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    # 自分の面接セッションか確認
    interview_session = conn.execute("""
        SELECT id
        FROM mock_interview_sessions
        WHERE id = ?
        AND user_id = ?
    """, (
        session_id,
        session["user_id"]
    )).fetchone()

    if not interview_session:
        conn.close()
        flash("面接履歴が見つかりません。")
        return redirect(url_for("ai_interview_history"))

    # 質問・回答を削除
    conn.execute("""
        DELETE FROM mock_interview_history
        WHERE session_id = ?
        AND user_id = ?
    """, (
        session_id,
        session["user_id"]
    ))

    # 面接セッションを削除
    conn.execute("""
        DELETE FROM mock_interview_sessions
        WHERE id = ?
        AND user_id = ?
    """, (
        session_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    flash("面接履歴を削除しました。")

    return redirect(url_for("ai_interview_history"))
@app.route("/company-analysis", methods=["GET", "POST"])
def company_analysis():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    user = conn.execute("""
        SELECT is_pro
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if not user or user["is_pro"] != 1:
        conn.close()
        flash("AI企業分析はCareerHero Pro限定機能です。")
        return redirect(url_for("dashboard"))

    companies = conn.execute("""
        SELECT id, company_name, memo
        FROM companies
        WHERE user_id = ?
        ORDER BY company_name ASC
    """, (
        session["user_id"],
    )).fetchall()

    if request.method == "POST":

        company_id = request.form["company_id"]

        company = conn.execute("""
            SELECT id, company_name, memo
            FROM companies
            WHERE id = ?
            AND user_id = ?
        """, (
            company_id,
            session["user_id"]
        )).fetchone()

        if not company:
            conn.close()
            flash("企業が見つかりません。")
            return redirect(url_for("company_analysis"))

        prompt = f"""
あなたは就活をサポートするAIです。

以下の企業について、就活生向けに分析してください。

企業名：
{company["company_name"]}

企業メモ：
{company["memo"] or "特になし"}

以下の項目をわかりやすく整理してください。

1. この企業について考えられる特徴
2. 主な事業について
3. 求められそうな人物像
4. 就活でアピールするとよいポイント
5. ESで意識するとよいポイント
6. 面接で聞かれそうな質問
7. この企業を受ける前に準備しておくこと

※企業名だけから推測できない情報については、
断定せず「確認が必要」としてください。
"""

        response = client.responses.create(
            model="gpt-5.6-luna",
            input=prompt
        )

        result = response.output_text

        conn.execute("""
            INSERT INTO company_analysis_history(
                user_id,
                company_id,
                result
            )
            VALUES (?, ?, ?)
        """, (
            session["user_id"],
            company["id"],
            result
        ))

        conn.commit()
        conn.close()

        return render_template(
            "company_analysis.html",
            companies=companies,
            result=result,
            company=company
        )

    conn.close()

    return render_template(
        "company_analysis.html",
        companies=companies
    )
@app.route("/company-analysis-history")
def company_analysis_history():

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    histories = conn.execute("""
        SELECT
            company_analysis_history.id,
            company_analysis_history.company_id,
            company_analysis_history.created_at,
            companies.company_name
        FROM company_analysis_history
        JOIN companies
            ON company_analysis_history.company_id = companies.id
        WHERE company_analysis_history.user_id = ?
        ORDER BY company_analysis_history.created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "company_analysis_history.html",
        histories=histories
    )
@app.route("/company-analysis-history/<int:history_id>")
def company_analysis_history_detail(history_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    history = conn.execute("""
        SELECT
            company_analysis_history.id,
            company_analysis_history.company_id,
            company_analysis_history.result,
            company_analysis_history.created_at,
            companies.company_name
        FROM company_analysis_history
        JOIN companies
            ON company_analysis_history.company_id = companies.id
        WHERE company_analysis_history.id = ?
        AND company_analysis_history.user_id = ?
    """, (
        history_id,
        session["user_id"]
    )).fetchone()

    conn.close()

    if not history:
        flash("企業分析履歴が見つかりません。")
        return redirect(url_for("company_analysis_history"))

    return render_template(
        "company_analysis_history_detail.html",
        history=history
    )
@app.route("/company-analysis-history/<int:history_id>/delete", methods=["POST"])
def delete_company_analysis_history(history_id):

    if "username" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    history = conn.execute("""
        SELECT id
        FROM company_analysis_history
        WHERE id = ?
        AND user_id = ?
    """, (
        history_id,
        session["user_id"]
    )).fetchone()

    if not history:
        conn.close()
        flash("企業分析履歴が見つかりません。")
        return redirect(url_for("company_analysis_history"))

    conn.execute("""
        DELETE FROM company_analysis_history
        WHERE id = ?
        AND user_id = ?
    """, (
        history_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    flash("企業分析履歴を削除しました。")

    return redirect(url_for("company_analysis_history"))
@app.route("/pro")
def pro():

    if "username" not in session:
        return redirect(url_for("login"))

    return render_template("pro.html")
@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():

    if "username" not in session:
        return redirect(url_for("login"))

    checkout_session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[
            {
                "price": "price_1UISR80hpDTUBRoZj7Lg40nn",
                "quantity": 1,
            }
        ],
        mode="subscription",
        client_reference_id=session["username"],
        success_url=url_for("dashboard", _external=True),
        cancel_url=url_for("pro", _external=True),
    )

    return redirect(checkout_session.url)
@app.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():

    payload = request.data
    sig_header = request.headers.get("Stripe-Signature")

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            webhook_secret
        )
    except ValueError:
        return "", 400
    except stripe.error.SignatureVerificationError:
        return "", 400

    if event["type"] == "checkout.session.completed":

        checkout_session = event["data"]["object"]

        username = checkout_session.get("client_reference_id")

        if username:
            conn = get_db()

            conn.execute("""
                UPDATE users
                SET is_pro = 1
                WHERE username = ?
            """, (username,))

            conn.commit()
            conn.close()

    return "", 200
@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
