#!/usr/bin/env python3
"""
Initialize Quote System Database Collections

This script sets up the database collections and indexes needed for the quote system.
Run this after setting up the main database to add quote functionality.
"""

import os
import sys
from flask import Flask
from flask_pymongo import PyMongo
from models import DatabaseManager

def create_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/nook_hook_app')
    
    # Initialize MongoDB
    mongo = PyMongo(app)
    app.mongo = mongo
    
    return app

def initialize_quote_system():
    """Initialize the quote system database collections and indexes"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Initializing quote system database...")
            
            # Create quotes collection if it doesn't exist
            existing_collections = app.mongo.db.list_collection_names()
            
            if 'quotes' not in existing_collections:
                app.mongo.db.create_collection('quotes')
                print("✓ Created 'quotes' collection")
            else:
                print("✓ 'quotes' collection already exists")
            
            if 'transactions' not in existing_collections:
                app.mongo.db.create_collection('transactions')
                print("✓ Created 'transactions' collection")
            else:
                print("✓ 'transactions' collection already exists")
            
            # Create indexes for quotes collection
            print("Creating indexes for quotes collection...")
            app.mongo.db.quotes.create_index([("user_id", 1), ("status", 1)])
            app.mongo.db.quotes.create_index([("user_id", 1), ("submitted_at", -1)])
            app.mongo.db.quotes.create_index([("book_id", 1), ("user_id", 1)])
            app.mongo.db.quotes.create_index("status")
            app.mongo.db.quotes.create_index("submitted_at")
            print("✓ Created quotes indexes")
            
            # Create indexes for transactions collection
            print("Creating indexes for transactions collection...")
            app.mongo.db.transactions.create_index([("user_id", 1), ("timestamp", -1)])
            app.mongo.db.transactions.create_index([("user_id", 1), ("status", 1)])
            app.mongo.db.transactions.create_index("quote_id", sparse=True)
            app.mongo.db.transactions.create_index("reward_type")
            print("✓ Created transactions indexes")
            
            print("\n🎉 Quote system database initialization completed successfully!")
            print("\nNext steps:")
            print("1. Start your Flask application")
            print("2. Login as admin and navigate to /quotes/admin/pending")
            print("3. Users can now submit quotes at /quotes/submit")
            print("4. Check the admin panel for quote verification")
            
        except Exception as e:
            print(f"❌ Error initializing quote system: {str(e)}")
            sys.exit(1)

if __name__ == '__main__':
    initialize_quote_system()