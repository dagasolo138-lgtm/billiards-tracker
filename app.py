"""Flask 主入口。

当前版本提供：
1. 应用初始化。
2. 启动时自动初始化数据库。
3. 首页：展示当前档位、该档位训练项目、最近练习记录。
4. 修改档位。
5. 新增练习记录。
6. 新增自定义训练项目。

后续可继续扩展：
- drill_logs 录入页
- 统计图表
- 档位升级建议
- 每周/月训练报表
"""

from __future__ import annotations

from flask import Flask, redirect, render_template, request, url_for

from database import (
    create_custom_drill,
    create_session,
    get_drills_by_level,
    get_recent_sessions,
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
        drill_logs 的详细录入可以在下一阶段单独追加。
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
