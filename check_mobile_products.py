#!/usr/bin/env python3
"""
检查移动代理产品
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.proxy import ProxyProduct
from app.core.config import settings

async def check_mobile_products():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession)
    
    async with async_session() as session:
        result = await session.execute(
            select(ProxyProduct).where(ProxyProduct.category == 'mobile')
        )
        products = result.scalars().all()
        
        print('=== 当前移动代理产品 ===')
        for product in products:
            print(f'ID: {product.id}')
            print(f'产品名: {product.product_name}')
            print(f'描述: {product.description}')
            print(f'价格: ${product.price}')
            print(f'时长: {product.duration_days} 天')
            print(f'提供商: {product.provider}')
            print(f'库存: {product.stock}')
            print(f'状态: {product.is_active}')
            print('---')

if __name__ == "__main__":
    asyncio.run(check_mobile_products())
