// Анимации при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    // Добавляем анимацию появления для всех карточек
    const cards = document.querySelectorAll('.card, .product-card, .stat-card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });

    // Обработка всплывающих сообщений
    setTimeout(() => {
        const flashMessages = document.querySelectorAll('.flash-message');
        flashMessages.forEach(message => {
            message.style.opacity = '1';
            setTimeout(() => {
                message.style.opacity = '0';
                message.style.transform = 'translateX(100%)';
                setTimeout(() => message.remove(), 300);
            }, 5000);
        });
    }, 1000);

    // Плавная прокрутка для якорных ссылок
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    window.scrollTo({
                        top: target.offsetTop - 80,
                        behavior: 'smooth'
                    });
                }
            }
        });
    });

    // Динамическое обновление количества товаров при покупке
    const buyButtons = document.querySelectorAll('.btn-buy');
    buyButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            const productCard = this.closest('.product-card');
            const quantityElement = productCard.querySelector('.product-quantity');
            
            // Показываем анимацию загрузки
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Покупка...';
            this.disabled = true;

            fetch(`/student/shop/buy/${productId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin'
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Обновляем количество товара
                    const currentQuantity = parseInt(quantityElement.textContent.match(/\d+/)[0]);
                    if (currentQuantity > 1) {
                        quantityElement.textContent = `В наличии: ${currentQuantity - 1} шт.`;
                    } else {
                        productCard.style.opacity = '0.5';
                        this.innerHTML = 'Закончился';
                        this.classList.remove('btn-primary');
                        this.classList.add('btn-secondary');
                    }
                    
                    // Обновляем баллы пользователя
                    const pointsElements = document.querySelectorAll('.user-points');
                    pointsElements.forEach(el => {
                        el.textContent = `${data.new_balance} баллов`;
                    });
                    
                    // Показываем уведомление
                    showNotification('Товар успешно куплен!', 'success');
                } else {
                    showNotification(data.error || 'Ошибка при покупке', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Произошла ошибка при покупке', 'error');
            })
            .finally(() => {
                this.innerHTML = originalText;
                this.disabled = false;
            });
        });
    });

    // Функция для показа уведомлений
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `flash-message flash-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i>
            ${message}
        `;
        
        const flashContainer = document.querySelector('.flash-messages');
        if (!flashContainer) {
            const container = document.createElement('div');
            container.className = 'flash-messages';
            document.body.appendChild(container);
            flashContainer = container;
        }
        
        flashContainer.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateX(100%)';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    // Обработка фильтрации товаров
    const categoryFilter = document.querySelector('#category-filter');
    if (categoryFilter) {
        categoryFilter.addEventListener('change', function() {
            const selectedCategory = this.value;
            const products = document.querySelectorAll('.product-card');
            
            products.forEach(product => {
                const productCategory = product.dataset.category;
                if (selectedCategory === 'all' || productCategory === selectedCategory) {
                    product.style.display = 'block';
                    setTimeout(() => {
                        product.style.opacity = '1';
                        product.style.transform = 'translateY(0)';
                    }, 50);
                } else {
                    product.style.opacity = '0';
                    product.style.transform = 'translateY(20px)';
                    setTimeout(() => {
                        product.style.display = 'none';
                    }, 300);
                }
            });
        });
    }

    // Обработка поиска
    const searchInput = document.querySelector('.search-input');
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            const searchTerm = this.value.toLowerCase();
            const items = document.querySelectorAll('.searchable-item');
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(searchTerm)) {
                    item.style.display = '';
                    setTimeout(() => {
                        item.style.opacity = '1';
                        item.style.transform = 'translateY(0)';
                    }, 50);
                } else {
                    item.style.opacity = '0';
                    item.style.transform = 'translateY(20px)';
                    setTimeout(() => {
                        item.style.display = 'none';
                    }, 300);
                }
            });
        });
    }

    // Анимация счетчиков в статистике
    const statNumbers = document.querySelectorAll('.stat-number');
    statNumbers.forEach(number => {
        const target = parseInt(number.textContent);
        const increment = target / 50;
        let current = 0;
        
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                current = target;
                clearInterval(timer);
            }
            number.textContent = Math.floor(current).toLocaleString();
        }, 30);
    });

    // Подтверждение опасных действий
    const dangerousButtons = document.querySelectorAll('.btn-danger, [data-confirm]');
    dangerousButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm || 'Вы уверены?')) {
                e.preventDefault();
                e.stopPropagation();
            }
        });
    });

    // Динамическая загрузка данных для фильтрации учеников
    const groupFilter = document.querySelector('#group-filter');
    if (groupFilter) {
        groupFilter.addEventListener('change', function() {
            const groupId = this.value;
            const studentTable = document.querySelector('#students-table tbody');
            
            if (studentTable) {
                studentTable.innerHTML = '<tr><td colspan="5" class="loading"><div class="spinner"></div></td></tr>';
                
                fetch(`/api/filter/students?group_id=${groupId}`)
                    .then(response => response.json())
                    .then(students => {
                        studentTable.innerHTML = '';
                        
                        if (students.length === 0) {
                            studentTable.innerHTML = '<tr><td colspan="5" class="text-center">Ученики не найдены</td></tr>';
                            return;
                        }
                        
                        students.forEach(student => {
                            const row = document.createElement('tr');
                            row.className = 'fade-in';
                            row.innerHTML = `
                                <td>${student.name}</td>
                                <td>${student.group}</td>
                                <td>${student.points} баллов</td>
                                <td>
                                    <a href="/admin/users/${student.id}" class="btn btn-primary btn-sm">
                                        <i class="fas fa-eye"></i>
                                    </a>
                                </td>
                            `;
                            studentTable.appendChild(row);
                        });
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        studentTable.innerHTML = '<tr><td colspan="5" class="text-center">Ошибка загрузки данных</td></tr>';
                    });
            }
        });
    }
    
    // Адаптация таблиц для мобильных устройств
    adaptTablesForMobile();
    
    // Улучшение работы форм на мобильных
    improveMobileForms();
});

// Функция для форматирования даты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Функция для форматирования чисел с пробелами
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

// Адаптация таблиц для мобильных устройств
function adaptTablesForMobile() {
    const tables = document.querySelectorAll('.table');
    
    tables.forEach(table => {
        // Проверяем, если таблица слишком широкая для экрана
        if (table.scrollWidth > window.innerWidth) {
            const wrapper = table.closest('.table-responsive');
            if (!wrapper) {
                const newWrapper = document.createElement('div');
                newWrapper.className = 'table-responsive';
                table.parentNode.insertBefore(newWrapper, table);
                newWrapper.appendChild(table);
            }
        }
    });
}

// Улучшение работы форм на мобильных устройствах
function improveMobileForms() {
    // Увеличиваем область нажатия для кнопок на мобильных
    if ('ontouchstart' in window) {
        const buttons = document.querySelectorAll('.btn, .sidebar-nav a, .page-link');
        buttons.forEach(button => {
            button.style.minHeight = '44px';
            button.style.minWidth = '44px';
            button.style.display = 'inline-flex';
            button.style.alignItems = 'center';
            button.style.justifyContent = 'center';
        });
        
        // Улучшаем работу выпадающих списков
        const selects = document.querySelectorAll('select');
        selects.forEach(select => {
            select.style.fontSize = '16px'; // Предотвращает масштабирование на iOS
        });
    }
}

// Обработка изменения ориентации экрана
window.addEventListener('orientationchange', function() {
    setTimeout(() => {
        adaptTablesForMobile();
        window.scrollTo(0, 0);
    }, 100);
});

// Обработка изменения размера окна
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        adaptTablesForMobile();
    }, 250);
});

// Экспорт функций для использования в других скриптах
window.Algoritmika = {
    formatDate,
    formatNumber,
    showNotification: function(message, type) {
        // Реализация из кода выше
    }
};

// Полифилл для старых браузеров
if (!String.prototype.includes) {
    String.prototype.includes = function(search, start) {
        'use strict';
        if (typeof start !== 'number') {
            start = 0;
        }
        
        if (start + search.length > this.length) {
            return false;
        } else {
            return this.indexOf(search, start) !== -1;
        }
    };
}