
import psycopg2

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="bank_management",
        user="postgres",
        password="12345678",
        port="5432"
    )

if __name__ == "__main__":
    try:
        conn = get_connection()
        print("PostgreSQL connected successfully!")
        conn.close()
    except psycopg2.Error as e:
        print("Database connection failed:", e)
