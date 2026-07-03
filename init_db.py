import os
import sys

from app import create_app, db
from app.config import Config
from werkzeug.security import generate_password_hash


def init_database():
    config = Config()
    db_dir = os.path.join(os.path.dirname(__file__), 'instance')
    os.makedirs(db_dir, exist_ok=True)
    os.makedirs(config.TESTS_FOLDER, exist_ok=True)
    os.makedirs(config.UPLOAD_FOLDER, exist_ok=True)

    app = create_app(config)

    with app.app_context():
        db.create_all()

        from app.models import Teacher

        if not Teacher.query.filter_by(username=config.TEACHER_USERNAME).first():
            teacher = Teacher(
                username=config.TEACHER_USERNAME,
                password_hash=generate_password_hash(config.TEACHER_PASSWORD)
            )
            db.session.add(teacher)
            db.session.commit()
            print(f'Учитель "{config.TEACHER_USERNAME}" создан.')
        else:
            print(f'Учитель "{config.TEACHER_USERNAME}" уже существует.')

        print('База данных успешно инициализирована.')


if __name__ == '__main__':
    init_database()
