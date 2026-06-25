import os
import sys

# Ajoute backend/ au sys.path pour que les imports fonctionnent sans installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Variable minimale pour que core.config ne plante pas au chargement
os.environ.setdefault("API_SECRET_KEY", "test_key_for_unit_tests_only_32chars!!")
os.environ.setdefault("JWT_SECRET_KEY", "test_jwt_key_for_unit_tests_only_48c!!")
