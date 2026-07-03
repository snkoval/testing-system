class TestAppStartup:
    def test_app_creates_successfully(self, app):
        assert app is not None

    def test_app_has_sqlalchemy_initialized(self, app):
        assert 'sqlalchemy' in app.extensions

    def test_index_page_returns_200(self, client):
        response = client.get('/')
        assert response.status_code == 200

    def test_config_has_required_settings(self, app):
        assert app.config['SECRET_KEY'] is not None
        assert 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']

    def test_default_limits_configured(self, app):
        assert app.config['DEFAULT_TIME_LIMIT'] == 1
        assert app.config['DEFAULT_MEMORY_LIMIT'] == 256

    def test_compiler_paths_configured(self, app):
        assert app.config['PYTHON_EXEC'] is not None
        assert app.config['CPP_COMPILER'] is not None
