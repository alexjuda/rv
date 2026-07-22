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
    author = CharField(null=True)
    base_branch = CharField()
    head_branch = CharField()
    state = CharField()
    latest_commit = CharField()
    synced_at = DateTimeField()

    class Meta:
        database = db
        table_name = "pr"
        indexes = ((("owner", "repo", "number"), True),)


class ReviewModel(Model):
    id = CharField(primary_key=True)
    pr = ForeignKeyField(PRModel, backref="reviews", on_delete="CASCADE")
    author = CharField(null=True)
    body = TextField()
    created_at = DateTimeField()
    state = CharField()
    commit = CharField(null=True)

    class Meta:
        database = db
        table_name = "review"


class ThreadModel(Model):
    id = CharField(primary_key=True)
    pr = ForeignKeyField(PRModel, backref="threads", on_delete="CASCADE")
    is_resolved = BooleanField()
    path = CharField(null=True)
    line = IntegerField(null=True)
    commit_sha = CharField()
    # NULL means the thread was not created as part of a review.
    review = ForeignKeyField(
        ReviewModel, null=True, backref="threads", on_delete="SET NULL"
    )

    class Meta:
        database = db
        table_name = "thread"


class ThreadCommentModel(Model):
    id = CharField(primary_key=True)
    thread = ForeignKeyField(ThreadModel, backref="comments", on_delete="CASCADE")
    body = TextField()
    author = CharField(null=True)
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "thread_comment"


class PRCommentModel(Model):
    id = CharField(primary_key=True)
    pr = ForeignKeyField(PRModel, backref="pr_comments", on_delete="CASCADE")
    author = CharField(null=True)
    body = TextField()
    created_at = DateTimeField()

    class Meta:
        database = db
        table_name = "pr_comment"


MODELS = [PRModel, ReviewModel, ThreadModel, ThreadCommentModel, PRCommentModel]
