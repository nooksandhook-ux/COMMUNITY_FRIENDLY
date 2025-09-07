from flask import current_app
from blueprints.rewards.services import RewardService
from bson import ObjectId
from datetime import datetime

class DonorRewardService(RewardService):
    """Service class for handling donor-specific rewards and leaderboards"""

    DONOR_BADGES = {
        'bronze': {'id': 'donor_bronze', 'name': 'Bronze Sponsor', 'description': 'Donated at Bronze tier', 'icon': '🥉', 'points': 100},
        'silver': {'id': 'donor_silver', 'name': 'Silver Sponsor', 'description': 'Donated at Silver tier', 'icon': '🥈', 'points': 250},
        'gold': {'id': 'donor_gold', 'name': 'Gold Sponsor', 'description': 'Donated at Gold tier', 'icon': '🥇', 'points': 500}
    }

    @staticmethod
    def award_donor_badge(user_id, tier):
        """Award a donor badge based on tier"""
        if tier not in DonorRewardService.DONOR_BADGES:
            return False

        badge = DonorRewardService.DONOR_BADGES[tier]
        badge_id = badge['id']
        description = badge['description']
        points = badge['points']

        # Check if badge already awarded
        if not RewardService._has_badge(user_id, badge_id):
            RewardService._award_badge(user_id, badge_id, description)
            RewardService.award_points(
                user_id=user_id,
                points=points,
                source='donation',
                description=f'Earned {badge["name"]} badge for donation',
                category='donation'
            )
            from models import ActivityLogger
            ActivityLogger.log_activity(
                user_id=user_id,
                action='badge_earned',
                description=f'Awarded {badge["name"]} badge',
                metadata={'badge_id': badge_id}
            )
        return True

    @staticmethod
    def get_donor_leaderboard(limit=10):
        """Get top donors leaderboard"""
        pipeline = [
            {'$match': {'status': 'completed'}},
            {'$group': {
                '_id': '$user_id',
                'total_donations': {'$sum': '$amount'},
                'donation_count': {'$sum': 1}
            }},
            {'$sort': {'total_donations': -1}},
            {'$limit': limit}
        ]
        leaderboard_data = list(current_app.mongo.db.donations.aggregate(pipeline))
        
        leaderboard = []
        for entry in leaderboard_data:
            user = current_app.mongo.db.users.find_one({'_id': entry['_id']})
            if user:
                leaderboard.append({
                    'username': user['username'],
                    'total_donations': entry['total_donations'],
                    'donation_count': entry['donation_count'],
                    'level': RewardService.calculate_level(RewardService.get_user_total_points(entry['_id']))
                })

        return leaderboard
