import psycopg

passwords = ['postgres', 'admin', 'root', '123456', 'password', '', 'sih_pass', 'kunal']
connected = False

for pwd in passwords:
    try:
        conn = psycopg.connect(dbname='postgres', user='postgres', password=pwd, host='localhost', port=5432)
        print(f"Connected to postgres with password: {repr(pwd)}")
        conn.autocommit = True
        cur = conn.cursor()
        
        # Check / Create role sih_user
        cur.execute("SELECT 1 FROM pg_roles WHERE rolname = 'sih_user'")
        if not cur.fetchone():
            cur.execute("CREATE ROLE sih_user WITH LOGIN PASSWORD 'sih_pass' SUPERUSER CREATEDB;")
            print("Created role sih_user with SUPERUSER CREATEDB")
        else:
            cur.execute("ALTER ROLE sih_user WITH SUPERUSER CREATEDB PASSWORD 'sih_pass';")
            print("Updated role sih_user")
            
        # Check / Create database sih_db
        cur.execute("SELECT 1 FROM pg_database WHERE datname = 'sih_db'")
        if not cur.fetchone():
            cur.execute("CREATE DATABASE sih_db OWNER sih_user;")
            print("Created database sih_db")
        else:
            print("Database sih_db already exists")
            
        conn.close()
        
        # Connect to sih_db and enable PostGIS
        conn2 = psycopg.connect(dbname='sih_db', user='postgres', password=pwd, host='localhost', port=5432)
        conn2.autocommit = True
        cur2 = conn2.cursor()
        try:
            cur2.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            print("PostGIS extension created successfully on sih_db")
        except Exception as e:
            print(f"Could not enable PostGIS: {e}")
        conn2.close()
        
        connected = True
        break
    except Exception as e:
        print(f"Attempt failed for password {repr(pwd)}: {e}")

if not connected:
    print("Could not connect to postgres with common passwords")
