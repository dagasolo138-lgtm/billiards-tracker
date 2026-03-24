"""Flask 主入口。

当前版本提供：
1. 应用初始化。
2. 启动时自动初始化数据库。
3. 首页：展示当前档位、该档位训练项目、最近练习记录。
4. 修改档位。
5. 新增练习记录。
6. 新增自定义训练项目。
7. drill_logs 录入页与批量保存。

后续可继续扩展：
- 统计图表
- 档位升级建议
- 每周/月训练报表
"""

from __future__ import annotations

from flask import Flask, abort, redirect, render_template, request, url_for

from database import (
    create_custom_drill,
    create_drill_log,
    create_session,
    delete_drill_logs_by_session,
    get_drill_logs_by_session,
    get_drills_by_level,
    get_recent_sessions,
    get_session_by_id,
    get_user_settings,
    init_db,
    update_user_level,
)


def create_app() -> Flask:
    """应用工厂。

    用应用工厂而不是直接写全局 app，后续更容易扩展配置、蓝图和测试。
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-key-for-local-use"

    # 启动时初始化数据库。
    init_db()

    @app.route("/")
    def index():
        """首页：展示当前档位、训练项目、近期练习。"""
        user_settings = get_user_settings()
        current_level = user_settings["current_level"] if user_settings else 1

        drills = get_drills_by_level(current_level)
        recent_sessions = get_recent_sessions(limit=10)

        return render_template(
            "index.html",
            current_level=current_level,
            drills=drills,
            recent_sessions=recent_sessions,
        )

    @app.post("/settings/level")
    def set_level():
        """更新用户当前档位。"""
        level = int(request.form.get("level", 1))
        update_user_level(level)
        return redirect(url_for("index"))

    @app.post("/sessions/new")
    def add_session():
        """新增练习主记录。

        这里只记录 session 主表。
        drill_logs 的详细录入可以在新增页面中继续补充。
        """
        practice_date = request.form.get("practice_date", "").strip()
        total_duration_minutes = int(request.form.get("total_duration_minutes", 0))
        state_rating = int(request.form.get("state_rating", 3))
        note = request.form.get("note", "").strip()

        if practice_date:
            create_session(
                practice_date=practice_date,
                total_duration_minutes=total_duration_minutes,
                state_rating=state_rating,
                note=note,
            )

        return redirect(url_for("index"))

    @app.get("/sessions/<int:session_id>/drills")
    def session_drills(session_id: int):
        """展示某次练习的 drill_logs 录入页。"""
        session = get_session_by_id(session_id)
        if not session:
            abort(404)

        user_settings = get_user_settings()
        current_level = user_settings["current_level"] if user_settings else 1
        drills = get_drills_by_level(current_level)
        existing_logs = get_drill_logs_by_session(session_id)

        # 以 drill_id 为键，便于模板直接回填已有数据。
        existing_log_map = {log["drill_id"]: log for log in existing_logs}

        return render_template(
            "drill_log.html",
            session=session,
            current_level=current_level,
            drills=drills,
            existing_log_map=existing_log_map,
        )

    @app.post("/sessions/<int:session_id>/drills")
    def save_session_drills(session_id: int):
        """批量保存某次练习下的所有项目记录。"""
        session = get_session_by_id(session_id)
        if not session:
            abort(404)

        user_settings = get_user_settings()
        current_level = user_settings["current_level"] if user_settings else 1
        drills = get_drills_by_level(current_level)

        # 采用“先清空后重写”的方式，保证同一次 session 的详情可以重复编辑。
        delete_drill_logs_by_session(session_id)

        for drill in drills:
            drill_id = drill["id"]
            set_count_raw = request.form.get(f"set_count_{drill_id}", "").strip()
            success_rate_raw = request.form.get(f"success_rate_{drill_id}", "").strip()
            subjective_difficulty_raw = request.form.get(
                f"subjective_difficulty_{drill_id}", ""
            ).strip()

            # 三项都为空时，视为该项目本次未录入，直接跳过。
            if not any([set_count_raw, success_rate_raw, subjective_difficulty_raw]):
                continue

            set_count = max(1, int(set_count_raw or 1))
            success_rate = min(100, max(0, float(success_rate_raw or 0)))
            subjective_difficulty = min(5, max(1, int(subjective_difficulty_raw or 3)))

            create_drill_log(
                session_id=session_id,
                drill_id=drill_id,
                set_count=set_count,
                success_rate=success_rate,
                subjective_difficulty=subjective_difficulty,
            )

        return redirect(url_for("session_drills", session_id=session_id))

    @app.post("/drills/custom")
    def add_custom_drill():
        """新增自定义训练项目。"""
        name = request.form.get("name", "").strip()
        target_count = int(request.form.get("default_target_count", 1))
        set_size = int(request.form.get("default_set_size", 15))
        level = int(request.form.get("level", 1))

        if name:
            create_custom_drill(
                name=name,
                default_target_count=target_count,
                default_set_size=set_size,
                level=level,
            )

        return redirect(url_for("index"))

    return app


app = create_app()


if __name__ == "__main__":
    # 本地开发默认开启 debug。
    app.run(debug=True)
