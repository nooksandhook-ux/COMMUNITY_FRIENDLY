#!/usr/bin/env python3
"""
Database Initialization Script for Nook & Hook

This script initializes the database with all required collections,
indexes, and default data including the admin user.

Usage:
    python init_db.py

Environment Variables Required:
    - MONGO_URI: MongoDB connection string
    - ADMIN_USERNAME: Admin username (default: admin)
    - ADMIN_PASSWORD: Admin password (default: admin123)
    - ADMIN_EMAIL: Admin email (default: admin@nookhook.com)
"""

import os
import sys
from flask import Flask
from flask_pymongo import PyMongo
from models import DatabaseManager
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_init_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'init-secret-key')
    app.config['MONGO_URI'] = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/nook_hook_app')
    
    # Initialize MongoDB
    mongo = PyMongo(app)
    app.mongo = mongo
    
    return app

def main():
    """Main initialization function"""
    logger.info("Starting Nook & Hook database initialization...")
    
    # Check for required environment variables
    required_vars = ['MONGO_URI']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("Please set the following environment variables:")
        logger.info("  MONGO_URI: MongoDB connection string")
        logger.info("  ADMIN_USERNAME: Admin username (optional, default: admin)")
        logger.info("  ADMIN_PASSWORD: Admin password (optional, default: admin123)")
        logger.info("  ADMIN_EMAIL: Admin email (optional, default: admin@nookhook.com)")
        sys.exit(1)
    
    # Create Flask app
    app = create_init_app()
    
    # Initialize database within app context
    with app.app_context():
        try:
            logger.info("Connecting to MongoDB...")
            # Test connection
            app.mongo.db.command('ping')
            logger.info("Successfully connected to MongoDB")
            
            # Initialize database
            success = DatabaseManager.initialize_database()
            
            if success:
                logger.info("✅ Database initialization completed successfully!")
                logger.info("Default admin credentials:")
                logger.info(f"  Username: {os.environ.get('ADMIN_USERNAME', 'admin')}")
                logger.info(f"  Password: {os.environ.get('ADMIN_PASSWORD', 'admin123')}")
                logger.info(f"  Email: {os.environ.get('ADMIN_EMAIL', 'admin@nookhook.com')}")
                logger.info("")
                logger.info("🚀 Your Nook & Hook application is ready to use!")
                logger.info("You can now start the application with: python app.py")
            else:
                logger.error("❌ Database initialization failed!")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {str(e)}")
            logger.error("Please check your MongoDB connection and try again.")
            sys.exit(1)

if __name__ == '__main__':
    main()