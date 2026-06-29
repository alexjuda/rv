from peewee import (
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

db = SqliteDatabase(None)


class PRModel(Model):
    owner = CharField()
    repo = CharField()
    number = IntegerField()
    url = CharField()
    title = CharField()
    author = CharField()
    base_branch = CharField()
    head_branch = CharField()
    state = CharField()
    latest_commit = CharField()
    synced_at = DateTimeField()

    class Meta:
        database = db
        table_name = "pr"
        indexes = ((("owner", "repo", "number"), True),)


class ThreadModel(Model):
    id = CharField(primary_key=True)
    pr = ForeignKeyField(PRModel, backref="threads", on_delete="CASCADE")
    is_resolved = BooleanField()
    path = CharField()
    line = IntegerField()
    commit_sha = CharField()

    class Meta:
        database = db
        table_name = "thread"


class ThreadCommentModel(Model):
    id = CharField(primary_key=True)
    thread = ForeignKeyField(ThreadModel, backref="comments", on_delete="CASCADE")
    body = TextField()
    author = CharField()
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "thread_comment"


class PRCommentModel(Model):
    id = CharField(primary_key=True)
    pr = ForeignKeyField(PRModel, backref="pr_comments", on_delete="CASCADE")
    author = CharField()
    body = TextField()
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "pr_comment"


class ReviewModel(Model):
    id = CharField(primary_key=True)
    pr = ForeignKeyField(PRModel, backref="reviews", on_delete="CASCADE")
    author = CharField()
    body = TextField()
    created_at = DateTimeField()
    state = CharField()
    commit = CharField()

    class Meta:
        database = db
        table_name = "review"


MODELS = [PRModel, ThreadModel, ThreadCommentModel, PRCommentModel, ReviewModel]
