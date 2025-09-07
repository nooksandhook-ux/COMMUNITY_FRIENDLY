from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from wtforms import DecimalField, SelectField, SubmitField
from wtforms.validators import DataRequired, NumberRange
from bson import ObjectId
from datetime import datetime
import logging
from blueprints.integrations.payment import OpayPayment
from blueprints.donations.donor_services import DonorRewardService
from . import donations_bp  # Import the Blueprint from __init__.py

logger = logging.getLogger(__name__)

class DonationForm(FlaskForm):
    amount = DecimalField('Donation Amount (NGN)', validators=[DataRequired(), NumberRange(min=1000)])
    tier = SelectField('Sponsorship Tier', choices=[
        ('bronze', 'Bronze (₦1,000 - ₦9,999)'),
        ('silver', 'Silver (₦10,000 - ₦49,999)'),
        ('gold', 'Gold (₦50,000+)')
    ], validators=[DataRequired()])
    submit = SubmitField('Proceed to Payment')

@donations_bp.route('/donate', methods=['GET', 'POST'])
@login_required
def donate():
    form = DonationForm()
    user_id = ObjectId(current_user.id)
    
    if form.validate_on_submit():
        try:
            amount = form.amount.data
            tier = form.tier.data
            
            # Validate amount against tier
            if tier == 'bronze' and (amount < 1000 or amount > 9999):
                flash('Bronze tier requires amount between ₦1,000 and ₦9,999', 'error')
                return render_template('donations/donate.html', form=form)
            elif tier == 'silver' and (amount < 10000 or amount > 49999):
                flash('Silver tier requires amount between ₦10,000 and ₦49,999', 'error')
                return render_template('donations/donate.html', form=form)
            elif tier == 'gold' and amount < 50000:
                flash('Gold tier requires amount of ₦50,000 or more', 'error')
                return render_template('donations/donate.html', form=form)
            
            # Initialize Opay payment
            payment = OpayPayment()
            payment_data = {
                'amount': int(amount * 100),  # Convert to kobo
                'currency': 'NGN',
                'user_id': str(user_id),
                'description': f'Nooks Donation - {tier.title()} Tier',
                'callback_url': url_for('donations.payment_callback', _external=True),
                'return_url': url_for('donations.payment_success', _external=True)
            }
            
            response = payment.initiate_payment(payment_data)
            if response.get('status') == 'success':
                # Store pending donation
                donation_data = {
                    'user_id': user_id,
                    'amount': amount,
                    'tier': tier,
                    'transaction_id': response.get('transaction_id'),
                    'status': 'pending',
                    'created_at': datetime.utcnow()
                }
                current_app.mongo.db.donations.insert_one(donation_data)
                
                # Log activity
                from models import ActivityLogger
                ActivityLogger.log_activity(
                    user_id=user_id,
                    action='donation_initiated',
                    description=f'Initiated {tier.title()} tier donation of ₦{amount}',
                    metadata={'transaction_id': response.get('transaction_id')}
                )
                
                return redirect(response.get('payment_url'))
            else:
                flash('Failed to initiate payment. Please try again.', 'error')
                logger.error(f"Payment initiation failed for user {user_id}: {response.get('message')}")
        
        except Exception as e:
            flash('An error occurred while processing your donation.', 'error')
            logger.error(f"Donation error for user {user_id}: {str(e)}", exc_info=True)
    
    return render_template('donations/donate.html', form=form)

@donations_bp.route('/payment/callback', methods=['POST'])
def payment_callback():
    try:
        payment = OpayPayment()
        webhook_data = request.json
        
        # Verify webhook signature (implement as per Opay docs)
        if not payment.verify_webhook(webhook_data):
            logger.error("Invalid webhook signature")
            return jsonify({'status': 'error', 'message': 'Invalid signature'}), 400
        
        transaction_id = webhook_data.get('transaction_id')
        status = webhook_data.get('status')
        
        donation = current_app.mongo.db.donations.find_one({'transaction_id': transaction_id})
        if not donation:
            logger.error(f"Donation not found for transaction {transaction_id}")
            return jsonify({'status': 'error', 'message': 'Donation not found'}), 404
        
        user_id = donation['user_id']
        amount = donation['amount']
        tier = donation['tier']
        
        if status == 'SUCCESS':
            # Update donation status
            current_app.mongo.db.donations.update_one(
                {'transaction_id': transaction_id},
                {'$set': {'status': 'completed', 'completed_at': datetime.utcnow()}}
            )
            
            # Award donor badge
            DonorRewardService.award_donor_badge(user_id, tier)
            
            # Log activity
            from models import ActivityLogger
            ActivityLogger.log_activity(
                user_id=user_id,
                action='donation_completed',
                description=f'Completed {tier.title()} tier donation of ₦{amount}',
                metadata={'transaction_id': transaction_id}
            )
            
            return jsonify({'status': 'success'})
        else:
            current_app.mongo.db.donations.update_one(
                {'transaction_id': transaction_id},
                {'$set': {'status': 'failed', 'failed_at': datetime.utcnow()}}
            )
            logger.error(f"Payment failed for transaction {transaction_id}: {webhook_data.get('message')}")
            return jsonify({'status': 'error', 'message': 'Payment failed'}), 400
    
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}", exc_info=True)
        return jsonify({'status': 'error', 'message': 'Webhook processing failed'}), 500

@donations_bp.route('/payment/success')
@login_required
def payment_success():
    flash('Thank you for your donation! Your support helps sustain Nooks.', 'success')
    return redirect(url_for('general.home'))


