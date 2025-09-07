from flask import Blueprint, render_template, jsonify, send_file
from flask_caching import Cache
from bson import ObjectId
from datetime import datetime, timedelta
import io
import csv
import logging
from flask import current_app
from . import analytics_bp, cache  # Import both analytics_bp and cache from __init__.py

logger = logging.getLogger(__name__)

@analytics_bp.route('/transparency')
@cache.cached(timeout=300)  # Cache for 5 minutes
def transparency():
    try:
        # Total donations
        donation_stats = current_app.mongo.db.donations.aggregate([
            {'$match': {'status': 'completed'}},
            {'$group': {
                '_id': None,
                'total_amount': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }}
        ])
        donation_stats = list(donation_stats)
        total_donations = donation_stats[0]['total_amount'] if donation_stats else 0
        donation_count = donation_stats[0]['count'] if donation_stats else 0

        # Verified quotes
        verified_quotes = current_app.mongo.db.quotes.count_documents({'status': 'verified'})

        # Active users (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users = current_app.mongo.db.users.count_documents({
            'last_login': {'$gte': thirty_days_ago}
        })

        # Donation breakdown by tier
        tier_breakdown = current_app.mongo.db.donations.aggregate([
            {'$match': {'status': 'completed'}},
            {'$group': {
                '_id': '$tier',
                'count': {'$sum': 1},
                'total': {'$sum': '$amount'}
            }}
        ])
        tier_data = {item['_id']: {'count': item['count'], 'total': item['total']} for item in tier_breakdown}

        return render_template('analytics/transparency.html',
                             total_donations=total_donations,
                             donation_count=donation_count,
                             verified_quotes=verified_quotes,
                             active_users=active_users,
                             tier_data=tier_data)

    except Exception as e:
        logger.error(f"Transparency dashboard error: {str(e)}", exc_info=True)
        return render_template('analytics/transparency.html', error="Unable to load statistics")

@analytics_bp.route('/analytics/report')
def export_report():
    try:
        # Generate CSV report
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Metric', 'Value', 'Date'])

        # Total donations
        donation_stats = current_app.mongo.db.donations.aggregate([
            {'$match': {'status': 'completed'}},
            {'$group': {
                '_id': None,
                'total_amount': {'$sum': '$amount'},
                'count': {'$sum': 1}
            }}
        ])
        donation_stats = list(donation_stats)
        total_donations = donation_stats[0]['total_amount'] if donation_stats else 0
        donation_count = donation_stats[0]['count'] if donation_stats else 0
        writer.writerow(['Total Donations (NGN)', total_donations, datetime.utcnow().isoformat()])
        writer.writerow(['Number of Donations', donation_count, datetime.utcnow().isoformat()])

        # Verified quotes
        verified_quotes = current_app.mongo.db.quotes.count_documents({'status': 'verified'})
        writer.writerow(['Verified Quotes', verified_quotes, datetime.utcnow().isoformat()])

        # Active users
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users = current_app.mongo.db.users.count_documents({
            'last_login': {'$gte': thirty_days_ago}
        })
        writer.writerow(['Active Users (Last 30 Days)', active_users, datetime.utcnow().isoformat()])

        # Donation tiers
        tier_breakdown = current_app.mongo.db.donations.aggregate([
            {'$match': {'status': 'completed'}},
            {'$group': {
                '_id': '$tier',
                'count': {'$sum': 1},
                'total': {'$sum': '$amount'}
            }}
        ])
        for item in tier_breakdown:
            writer.writerow([f'{item["_id"].title()} Tier Donations (NGN)', item['total'], datetime.utcnow().isoformat()])
            writer.writerow([f'{item["_id"].title()} Tier Count', item['count'], datetime.utcnow().isoformat()])

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'nooks_impact_report_{datetime.utcnow().strftime("%Y%m%d")}.csv'
        )

    except Exception as e:
        logger.error(f"Report export error: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Failed to generate report'}), 500
