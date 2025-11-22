import asyncio
import aiomysql
from app.core.config import settings

async def check_users():
    # 解析数据库URL
    db_url = settings.DATABASE_URL
    # mysql+aiomysql://manyproxy:YhrWRyZiYBhzTGbn@208.110.95.234:3306/manyproxy
    
    # 提取连接信息
    if db_url.startswith('mysql+aiomysql://'):
        connection_info = db_url.replace('mysql+aiomysql://', '')
        parts = connection_info.split('@')
        user_pass = parts[0].split(':')
        host_db = parts[1].split('/')
        
        username = user_pass[0]
        password = user_pass[1]
        host_port = host_db[0].split(':')
        host = host_port[0]
        port = int(host_port[1])
        database = host_db[1]
        
        print(f"连接信息: {username}@{host}:{port}/{database}")
        
        try:
            conn = await aiomysql.connect(
                host=host,
                port=port,
                user=username,
                password=password,
                db=database
            )
            
            cursor = await conn.cursor()
            await cursor.execute("SELECT id, username, email, is_admin FROM users")
            rows = await cursor.fetchall()
            
            print("用户数据:")
            print("ID | Username | Email | Is_Admin")
            print("-" * 50)
            for row in rows:
                print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")
            
            await cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"连接数据库失败: {e}")

if __name__ == "__main__":
    asyncio.run(check_users())
