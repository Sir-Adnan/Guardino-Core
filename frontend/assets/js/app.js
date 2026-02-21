/* مسیر: assets/js/app.js */

// مدیریت منوی موبایل
function toggleMenu() { 
    document.getElementById('navMenu').classList.toggle('active'); 
}

// تغییر حالت تاریک و روشن
function toggleTheme() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('g_theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
}

// تغییر رنگ اصلی پنل
function changeColor(c) {
    document.documentElement.style.setProperty('--primary', c);
    localStorage.setItem('g_color', c);
}

// لود کردن تم هنگام باز شدن صفحه
function initTheme() {
    if(localStorage.getItem('g_theme') === 'dark') document.body.classList.add('dark-mode');
    if(localStorage.getItem('g_color')) changeColor(localStorage.getItem('g_color'));
}
document.addEventListener('DOMContentLoaded', initTheme);

// --- سیستم اختصاصی نمایش پیام گوشه صفحه (Toast) ---
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `g-toast g-toast-${type}`;
    toast.innerHTML = message;
    document.body.appendChild(toast);
    
    // انیمیشن ورود
    setTimeout(() => toast.classList.add('show'), 10);
    
    // انیمیشن خروج و حذف بعد از 3 ثانیه
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 400);
    }, 3000);
}

// --- توابع مربوط به کاربران ---
function genU() {
    // لیست پیشوندهای بسیار متنوع
    const prefixes = ['user', 'vpn', 'net', 'acc', 'vip', 'pro', 'fast', 'max', 'turbo', 'sub', 'bot', 'go', 'top', 'plus'];
    const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
    let r = prefixes[Math.floor(Math.random() * prefixes.length)] + '_';
    for (let i = 0; i < 5; i++) r += chars.charAt(Math.floor(Math.random() * chars.length));
    if(document.getElementById('u_name')) document.getElementById('u_name').value = r;
}

function toggleEdit(id) { 
    let e = document.getElementById('edit-' + id); 
    if(e) e.style.display = (e.style.display === 'none' || e.style.display === '') ? 'flex' : 'none'; 
}

// کپی حرفه‌ای با پیام توست
async function copyS(text) {
    if(!text) { showToast('❌ لینک ساب وجود ندارد!', 'danger'); return; }
    try {
        await navigator.clipboard.writeText(text);
        showToast('✅ لینک کپی شد!');
    } catch (err) {
        // روش جایگزین برای مرورگرهای قدیمی
        let textArea = document.createElement("textarea");
        textArea.value = text;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
        showToast('✅ لینک کپی شد!');
    }
}
