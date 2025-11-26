#!/usr/bin/env python3
"""
检查最近的购买记录和余额变化
"""

import asyncio
import sys
import os
from decimal import Decimal

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.order import Order, Transaction, BalanceLog
from sqlalchemy.future import select
from datetime import datetime

async def check_recent_purchases():
    """检查最近的购买记录"""
    print("🔍 检查最近的购买记录和余额变化...")
    print("=" * 60)
    
    async with AsyncSessionLocal() as db:
        try:
            # 1. 获取用户当前信息
            print("1. 获取用户当前信息...")
            user_result = await db.execute(
                select(User).where(User.id == 2)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                print("❌ 用户不存在")
                return
            
            print(f"✅ 用户: {user.username}")
            print(f"   当前余额: {user.balance}")
            
            # 2. 获取所有订单记录
            print("\n2. 获取所有订单记录...")
            orders_result = await db.execute(
                select(Order).where(Order.user_id == user.id)
                .order_by(Order.created_at.asc())
            )
            orders = orders_result.scalars().all()
            
            print(f"✅ 找到 {len(orders)} 个订单:")
            for i, order in enumerate(orders, 1):
                print(f"   {i}. 订单号: {order.order_number}")
                print(f"      类型: {order.type}")
                print(f"      金额: {order.amount}")
                print(f"      状态: {order.status}")
                print(f"      描述: {order.description}")
                print(f"      创建时间: {order.created_at}")
                print(f"      完成时间: {order.completed_at}")
                print("      ---")
            
            # 3. 获取所有交易记录
            print("\n3. 获取所有交易记录...")
            transactions_result = await db.execute(
                select(Transaction).where(Transaction.user_id == user.id)
                .order_by(Transaction.created_at.asc())
            )
            transactions = transactions_result.scalars().all()
            
            print(f"✅ 找到 {len(transactions)} 个交易:")
            balance_history = []
            for i, transaction in enumerate(transactions, 1):
                print(f"   {i}. 交易ID: {transaction.transaction_id}")
                print(f"      类型: {transaction.type}")
                print(f"      金额: {transaction.amount}")
                print(f"      余额前: {transaction.balance_before}")
                print(f"      余额后: {transaction.balance_after}")
                print(f"      余额变化: {Decimal(transaction.balance_before) - Decimal(transaction.balance_after)}")
                print(f"      描述: {transaction.description}")
                print(f"      创建时间: {transaction.created_at}")
                print("      ---")
                
                balance_history.append({
                    'time': transaction.created_at,
                    'before': Decimal(transaction.balance_before),
                    'after': Decimal(transaction.balance_after),
                    'change': Decimal(transaction.balance_before) - Decimal(transaction.balance_after),
                    'description': transaction.description
                })
            
            # 4. 获取所有余额日志
            print("\n4. 获取所有余额日志...")
            balance_logs_result = await db.execute(
                select(BalanceLog).where(BalanceLog.user_id == user.id)
                .order_by(BalanceLog.created_at.asc())
            )
            balance_logs = balance_logs_result.scalars().all()
            
            print(f"✅ 找到 {len(balance_logs)} 个余额日志:")
            for i, log in enumerate(balance_logs, 1):
                print(f"   {i}. 类型: {log.type}")
                print(f"      金额: {log.amount}")
                print(f"      余额前: {log.balance_before}")
                print(f"      余额后: {log.balance_after}")
                print(f"      余额变化: {Decimal(log.balance_before) - Decimal(log.balance_after)}")
                print(f"      描述: {log.description}")
                print(f"      创建时间: {log.created_at}")
                print("      ---")
            
            # 5. 分析余额变化
            print("\n5. 分析余额变化...")
            if balance_history:
                print("余额变化历史:")
                initial_balance = balance_history[0]['before']
                current_balance = balance_history[-1]['after']
                total_deducted = sum(item['change'] for item in balance_history if item['change'] > 0)
                
                print(f"   初始余额: {initial_balance}")
                print(f"   当前余额: {current_balance}")
                print(f"   总扣除: {total_deducted}")
                print(f"   理论余额: {initial_balance - total_deducted}")
                
                if abs(current_balance - (initial_balance - total_deducted)) < Decimal('0.01'):
                    print("✅ 余额计算正确")
                else:
                    print("❌ 余额计算有误")
            
            # 6. 检查最近的购买是否扣费
            print("\n6. 检查最近的购买是否扣费...")
            if orders:
                latest_order = orders[-1]
                print(f"最近订单: {latest_order.order_number}")
                print(f"订单金额: {latest_order.amount}")
                print(f"订单状态: {latest_order.status}")
                
                # 查找对应的交易记录
                matching_transaction = None
                for transaction in transactions:
                    if transaction.order_id == latest_order.id:
                        matching_transaction = transaction
                        break
                
                if matching_transaction:
                    print(f"✅ 找到对应交易:")
                    print(f"   交易金额: {matching_transaction.amount}")
                    print(f"   余额前: {matching_transaction.balance_before}")
                    print(f"   余额后: {matching_transaction.balance_after}")
                    print(f"   实际扣除: {Decimal(matching_transaction.balance_before) - Decimal(matching_transaction.balance_after)}")
                    
                    if matching_transaction.amount == latest_order.amount:
                        print("✅ 交易金额与订单金额一致")
                    else:
                        print("❌ 交易金额与订单金额不一致")
                else:
                    print("❌ 未找到对应的交易记录")
            
            print("\n" + "=" * 60)
            print("🎉 购买记录检查完成")
            
        except Exception as e:
            print(f"❌ 检查过程中发生错误: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_recent_purchases())
