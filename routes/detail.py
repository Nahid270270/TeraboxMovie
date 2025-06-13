from flask import Blueprint, render_template

detail_bp = Blueprint('detail', __name__, url_prefix='/detail')

@detail_bp.route('/<int:item_id>')
def show_detail(item_id):
    # এখানে item_id ব্যবহার করে ডেটা লোড করার লজিক থাকবে
    return render_template('detail.html', item_id=item_id)
