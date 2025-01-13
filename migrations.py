import json

from lnbits.db import Database

db2 = Database("ext_lnurlpos")


async def m001_initial(db):
    """
    Initial lnurldevice table.
    """
    await db.execute(
        f"""
        CREATE TABLE lnurldevice.lnurldevices (
            id TEXT NOT NULL PRIMARY KEY,
            key TEXT NOT NULL,
            title TEXT NOT NULL,
            wallet TEXT NOT NULL,
            currency TEXT NOT NULL,
            device TEXT NOT NULL,
            profit FLOAT NOT NULL,
            timestamp TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )
    await db.execute(
        f"""
        CREATE TABLE lnurldevice.lnurldevicepayment (
            id TEXT NOT NULL PRIMARY KEY,
            deviceid TEXT NOT NULL,
            payhash TEXT,
            payload TEXT NOT NULL,
            pin INT,
            sats {db.big_int},
            timestamp TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m002_redux(db):
    """
    Moves everything from lnurlpos to lnurldevice
    """
    try:
        for row in [
            list(row) for row in await db2.fetchall("SELECT * FROM lnurlpos.lnurlposs")
        ]:
            await db.execute(
                """
                INSERT INTO lnurldevice.lnurldevices (
                    id,
                    key,
                    title,
                    wallet,
                    currency,
                    device,
                    profit
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (row[0], row[1], row[2], row[3], row[4], "pos", 0),
            )
        for row in [
            list(row)
            for row in await db2.fetchall("SELECT * FROM lnurlpos.lnurlpospayment")
        ]:
            await db.execute(
                """
                INSERT INTO lnurldevice.lnurldevicepayment (
                    id,
                    deviceid,
                    payhash,
                    payload,
                    pin,
                    sats
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (row[0], row[1], row[3], row[4], row[5], row[6]),
            )
    except Exception:
        pass


async def m003_redux(db):
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN amount INT DEFAULT 0;"
    )


async def m004_redux(db):
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN pin INT DEFAULT 0"
    )

    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN profit1 FLOAT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN amount1 INT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN pin1 INT DEFAULT 0"
    )

    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN profit2 FLOAT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN amount2 INT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN pin2 INT DEFAULT 0"
    )

    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN profit3 FLOAT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN amount3 INT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN pin3 INT DEFAULT 0"
    )

    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN profit4 FLOAT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN amount4 INT DEFAULT 0"
    )
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevices ADD COLUMN pin4 INT DEFAULT 0"
    )


async def m005_redux(db):
    """migrate to generate switches array as json"""

    new_db = "lnurldevice.lnurldevice"
    old_db = "lnurldevice.lnurldevices"

    # create new table with name in singular
    await db.execute(
        f"""
        CREATE TABLE {new_db} (
            id TEXT NOT NULL PRIMARY KEY,
            key TEXT NOT NULL,
            title TEXT NOT NULL,
            wallet TEXT NOT NULL,
            currency TEXT NOT NULL,
            device TEXT NOT NULL,
            profit FLOAT NOT NULL,
            switches TEXT,
            timestamp TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )
    # migration date from old table
    keys = "id,key,title,wallet,currency,device,profit,timestamp"
    await db.execute(f"INSERT INTO {new_db} ({keys}) SELECT {keys} FROM {old_db}")

    # migration from old switches to new ones
    rows = await db.execute(f"SELECT * FROM {old_db}")
    for row in await rows.fetchall():
        switches = []
        if row.amount > 0:
            switches.append(
                {
                    "amount": row.profit,
                    "pin": row.pin,
                    "duration": row.amount,
                }
            )
        if row.amount1 > 0:
            switches.append(
                {
                    "amount": row.profit1,
                    "pin": row.pin1,
                    "duration": row.amount1,
                }
            )
        if row.amount2 > 0:
            switches.append(
                {
                    "amount": row.profit2,
                    "pin": row.pin2,
                    "duration": row.amount2,
                }
            )
        if row.amount3 > 0:
            switches.append(
                {
                    "amount": row.profit3,
                    "pin": row.pin3,
                    "duration": row.amount3,
                }
            )
        if row.amount4 > 0:
            switches.append(
                {
                    "amount": row.profit4,
                    "pin": row.pin4,
                    "duration": row.amount4,
                }
            )
        await db.execute(
            f"UPDATE {new_db} set switches = ? where id = ?",
            (json.dumps(switches), row.id),
        )

    # drop old table columns
    await db.execute(f"DROP TABLE {old_db}")


async def m006_redux(db):
    # Rename switches so we can also use for atm
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevice RENAME COLUMN switches TO extra"
    )

async def m007_redux(db):
    await db.execute(
        "ALTER TABLE lnurldevice.lnurldevice ADD COLUMN description TEXT;"
    )
