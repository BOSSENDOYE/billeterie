"""Backend MySQL de Django, autorisant MariaDB 10.4 (version fournie par XAMPP).

Django 5.2 exige officiellement MariaDB >= 10.5 ; les fonctionnalités utilisées
ici fonctionnent en 10.4. En production, préférer MariaDB >= 10.5 / MySQL 8 et
repasser ENGINE à 'django.db.backends.mysql'.
"""
from django.db.backends.mysql import base, features


class DatabaseFeatures(features.DatabaseFeatures):
    @property
    def minimum_database_version(self):
        return (10, 4) if self.connection.mysql_is_mariadb else (8, 0, 11)

    # INSERT ... RETURNING n'existe qu'à partir de MariaDB 10.5
    @property
    def can_return_columns_from_insert(self):
        return not self.connection.mysql_is_mariadb or self.connection.mysql_version >= (10, 5)

    @property
    def can_return_rows_from_bulk_insert(self):
        return self.can_return_columns_from_insert


class DatabaseWrapper(base.DatabaseWrapper):
    features_class = DatabaseFeatures
