from flask import Blueprint, render_template

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
def admin_dashboard():
    return render_template('admin.html')

# অন্যান্য অ্যাডমিন রুট এখানে যোগ করুন, যেমন:
@admin_bp.route('/edit/<int:item_id>')
def edit_item(item_id):
    return render_template('edit.html', item_id=item_id)
