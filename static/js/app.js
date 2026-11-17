document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', function(e) {
            e.preventDefault();
            performSearch();
        });
    }

    const feedbackForm = document.getElementById('feedbackForm');
    if (feedbackForm) {
        feedbackForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            fetch('/feedback', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert(data.success, 'success');
                    const modal = bootstrap.Modal.getInstance(document.getElementById('feedbackModal'));
                    if (modal) {
                        modal.hide();
                    }
                    feedbackForm.reset();
                } else {
                    showAlert(data.error, 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred while submitting feedback.', 'danger');
            });
        });
    }

    const adminLoginForm = document.getElementById('adminLoginForm');
    if (adminLoginForm) {
        adminLoginForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const username = document.getElementById('admin_username').value.trim();
            const password = document.getElementById('admin_password').value.trim();

            if (!username || !password) {
                showAlert('Please enter username and password.', 'warning');
                return;
            }

            const formData = new FormData();
            formData.append('username', username);
            formData.append('password', password);

            fetch('/admin/login', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('adminLoginModal'));
                    if (modal) {
                        modal.hide();
                    }
                    window.location.href = data.redirect;
                } else {
                    showAlert(data.error || 'Invalid username or password!', 'danger');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showAlert('An error occurred during login.', 'danger');
            });
        });
    }
});

function performSearch() {
    const searchForm = document.getElementById('searchForm');
    if (!searchForm) {
        return;
    }

    const formData = new FormData(searchForm);
    const fromValue = formData.get('from')?.trim();
    const toValue = formData.get('to')?.trim();

    if (!fromValue || !toValue) {
        showAlert('Please enter both pickup and destination locations.', 'warning');
        return;
    }

    if (fromValue.toLowerCase() === toValue.toLowerCase()) {
        showAlert('Pickup and destination locations cannot be the same.', 'warning');
        return;
    }

    const submitButton = searchForm.querySelector('button[type="submit"]');
    if (!submitButton) {
        return;
    }

    const originalText = submitButton.innerHTML;
    submitButton.innerHTML = '<i class="bi bi-hourglass-split me-2"></i>Searching...';
    submitButton.disabled = true;

    fetch('/search', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        displayResult(data);
    })
    .catch(error => {
        console.error('Error:', error);
        showAlert('An error occurred while searching. Please try again.', 'danger');
    })
    .finally(() => {
        submitButton.innerHTML = originalText;
        submitButton.disabled = false;
    });
}

function displayResult(data) {
    const resultArea = document.getElementById('resultArea');
    const resultContent = document.getElementById('resultContent');
    if (!resultArea || !resultContent) {
        return;
    }

    if (data.error) {
        resultContent.innerHTML = `
            <div class="result-card">
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle-fill text-danger fs-1 mb-3"></i>
                    <h5 class="text-danger mb-2">Error</h5>
                    <p class="text-muted">${data.error}</p>
                </div>
            </div>
        `;
    } else if (data.fare === null) {
        resultContent.innerHTML = `
            <div class="result-card">
                <div class="text-center">
                    <i class="bi bi-exclamation-triangle text-warning fs-1 mb-3"></i>
                    <h5 class="text-muted mb-2">No route found</h5>
                    <p class="text-muted mb-3">Please submit feedback for this route.</p>
                    <button class="btn btn-outline-primary rounded-pill px-4" data-bs-toggle="modal" data-bs-target="#feedbackModal">
                        <i class="bi bi-chat-dots me-2"></i>Submit Feedback
                    </button>
                </div>
            </div>
        `;
    } else {
        let badgeClass = 'badge-verified';
        let badgeText = 'Verified Fare';
        let icon = 'bi-check-circle-fill';
        let explanation = 'Based on real local data';

        if (data.type === 'estimated') {
            badgeClass = 'badge-estimated';
            badgeText = 'Estimated Fare';
            icon = 'bi-graph-up';
            explanation = `Estimated with ${data.confidence}% confidence from ${data.contributors} contributors`;
        } else if (data.type === 'indirect') {
            badgeClass = 'bg-info';
            badgeText = 'Suggested Route';
            icon = 'bi-arrow-right-circle-fill';
            explanation = 'Suggested route based on available data';
        }

        resultContent.innerHTML = `
            <div class="result-card">
                <div class="fare-display">
                    <div class="fare-amount">${data.fare.toFixed(2)}</div>
                    <span class="fare-badge ${badgeClass}">
                        <i class="bi ${icon} me-1"></i>${badgeText}
                    </span>
                </div>
                <div class="route-display text-center mb-3">
                    <p class="mb-1 text-muted small">Route</p>
                    <p class="fw-semibold text-dark">${data.route.join(' → ')}</p>
                </div>
                <div class="fare-explanation">
                    ${explanation}
                </div>
                <div class="text-center mt-3">
                    <button class="btn btn-outline-light btn-sm rounded-pill px-3" data-bs-toggle="modal" data-bs-target="#feedbackModal">
                        <i class="bi bi-chat-dots me-1"></i>Submit Feedback
                    </button>
                </div>
            </div>
        `;
    }

    resultArea.style.display = 'block';
    resultArea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function showAlert(message, type = 'info') {
    const alertContainer = document.createElement('div');
    alertContainer.className = `alert alert-${type} alert-dismissible fade show`;
    alertContainer.style.cssText = 'position: fixed; top: 20px; right: 20px; z-index: 1050; max-width: 400px;';
    alertContainer.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(alertContainer);

    setTimeout(() => {
        alertContainer.remove();
    }, 5000);
}
