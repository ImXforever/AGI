/* =========================================================
   Kia-Agent Admin Dashboard – app.js
   Vanilla JS, no frameworks, no CDN dependencies
   Arabic-first RTL design
   ========================================================= */

(function () {
  'use strict';

  /* ---------------------------------------------------------
     1. I18N – Arabic / English translations
     --------------------------------------------------------- */
  const I18N = {
    ar: {
      dir: 'rtl',
      langLabel: 'English',
      loginTitle: 'لوحة تحكم المسؤول',
      loginSubtitle: 'Kia-Agent Platform',
      username: 'اسم المستخدم',
      password: 'كلمة المرور',
      loginBtn: 'تسجيل الدخول',
      loginError: 'خطأ في تسجيل الدخول',
      logout: 'تسجيل الخروج',
      nav_approvals: 'الموافقات',
      nav_customers: 'العملاء',
      nav_catalog: 'الكتالوج',
      nav_quotes: 'عروض الأسعار',
      nav_tickets: 'التذاكر',
      nav_analytics: 'التحليلات',
      nav_audit: 'سجل التدقيق',
      nav_templates: 'القوالب',
      nav_router: 'الموجه',
      emptyState: 'لا توجد بيانات',
      loading: 'جارٍ التحميل...',
      search: 'بحث...',
      approve: 'موافقة',
      reject: 'رفض',
      edit: 'تعديل',
      save: 'حفظ',
      cancel: 'إلغاء',
      reset: 'إعادة تعيين',
      confirm: 'تأكيد',
      status_pending: 'قيد الانتظار',
      status_approved: 'مقبول',
      status_rejected: 'مرفوض',
      status_active: 'نشط',
      status_inactive: 'غير نشط',
      countdown: 'الوقت المتبقي',
      days: 'أيام',
      hours: 'ساعات',
      minutes: 'دقائق',
      seconds: 'ثواني',
      customers_title: 'إدارة العملاء',
      catalog_title: 'إدارة الكتالوج',
      quotes_title: 'عروض الأسعار',
      tickets_title: 'التذاكر',
      analytics_title: 'التحليلات',
      audit_title: 'سجل التدقيق',
      templates_title: 'إدارة القوالب',
      approvals_title: 'طلبات الموافقة',
      router_title: 'الموجه',
      router_desc: 'إدارة قواعد التوجيه للعملاء والمبيعات',
      openRouter: 'فتح لوحة الموجه',
      importBtn: 'استيراد CSV',
      importReport: 'تقرير الاستيراد',
      totalCustomers: 'إجمالي العملاء',
      totalProducts: 'إجمالي المنتجات',
      totalQuotes: 'إجمالي عروض الأسعار',
      totalTickets: 'إجمالي التذاكر',
      revenue: 'الإيرادات',
      pending: 'قيد الانتظار',
      activeCount: 'نشط',
      closed: 'مغلق',
      name: 'الاسم',
      phone: 'الهاتف',
      email: 'البريد الإلكتروني',
      company: 'الشركة',
      source: 'المصدر',
      date: 'التاريخ',
      amount: 'المبلغ',
      status: 'الحالة',
      priority: 'الأولوية',
      subject: 'الموضوع',
      message: 'الرسالة',
      customer: 'العميل',
      actions: 'إجراءات',
      id: 'المعرف',
      product: 'المنتج',
      price: 'السعر',
      category: 'الفئة',
      unit: 'الوحدة',
      description: 'الوصف',
      notes: 'ملاحظات',
      decision: 'القرار',
      quoteNumber: 'رقم العرض',
      total: 'الإجمالي',
      details: 'التفاصيل',
      items: 'العناصر',
      createdAt: 'تاريخ الإنشاء',
      updatedAt: 'تاريخ التحديث',
      high: 'عالي',
      medium: 'متوسط',
      low: 'منخفض',
      templateKey: 'مفتاح القالب',
      templateLang: 'اللغة',
      templateBody: 'المحتوى',
      templateActive: 'نشط',
      yes: 'نعم',
      no: 'لا',
      analytics_query: 'استعلام مخصص',
      runQuery: 'تشغيل الاستعلام',
      queryResult: 'نتائج الاستعلام',
      selectTemplate: 'اختر القالب',
      overview: 'نظرة عامة',
      chart_topProducts: 'أكثر المنتجات طلباً',
      chart_sources: 'مصادر العملاء',
      chart_monthly: 'المبيعات الشهرية',
      sparks_last7: 'آخر 7 أيام',
      imported: 'تم الاستيراد',
      skipped: 'تم التخطي',
      errors: 'الأخطاء',
      row: 'صف',
      errorRow: 'خطأ',
      editApprovalTitle: 'تعديل الموافقة',
      originalText: 'النص الأصلي',
      editedText: 'النص المعدل',
      approvalNote: 'ملاحظة القرار',
      closeModal: 'إغلاق',
      sessionExpired: 'انتهت الجلسة',
      networkError: 'خطأ في الشبكة',
      noResults: 'لا توجد نتائج',
      totalRevenue: 'إجمالي الإيرادات',
      avgQuote: 'متوسط عرض السعر',
      conversionRate: 'معدل التحويل',
      topProducts: 'المنتجات الأكثر طلباً',
      sourcesBreakdown: 'توزيع المصادر',
      monthlySales: 'المبيعات الشهرية',
      recentActivity: 'النشاط الأخير',
      all: 'الكل',
      today: 'اليوم',
      thisWeek: 'هذا الأسبوع',
      thisMonth: 'هذا الشهر',
      noTemplates: 'لا توجد قوالب',
      saved: 'تم الحفظ',
      templateSaved: 'تم حفظ القالب',
      templateReset: 'تم إعادة تعيين القالب',
      productAdded: 'تمت إضافة المنتج',
      productUpdated: 'تم تحديث المنتج',
      productToggled: 'تم تغيير حالة المنتج',
      csvImportSuccess: 'تم استيراد ملف CSV بنجاح',
      csvImportPartial: 'تم الاستيراد مع بعض الأخطاء',
      csvImportFailed: 'فشل الاستيراد',
      confirmApprove: 'هل تريد الموافقة على هذا الطلب؟',
      confirmReject: 'هل تريد رفض هذا الطلب؟',
      pendingApprovals: 'طلبات تنتظر الموافقة',
      productForm: 'نموذج المنتج',
      productFormEdit: 'تعديل المنتج',
      productFormAdd: 'إضافة منتج جديد',
      noData: 'لا تتوفر بيانات',
      selectFile: 'اختر ملف CSV',
      importPreview: 'معاينة الاستيراد',
      headerRow: 'صف العناوين',
      dataRows: 'صفوف البيانات',
      uploaded: 'تم الرفع',
      templateQuery: 'استعلام القالب',
      params: 'المعاملات',
      enterParams: 'أدخل المعاملات بصيغة JSON',
      queryTemplate: 'قالب الاستعلام',
      noQueries: 'لا توجد استعلامات',
      run: 'تشغيل',
      result: 'النتيجة',
      queue: 'القائمة',
      connected: 'متصل',
      disconnected: 'غير متصل',
      streamError: 'خطأ في الاتصال المباشر',
      barChart: 'رسم بياني شريطي',
      sparkline: 'رسم بياني مصغر'
    },
    en: {
      dir: 'ltr',
      langLabel: 'العربية',
      loginTitle: 'Admin Dashboard',
      loginSubtitle: 'Kia-Agent Platform',
      username: 'Username',
      password: 'Password',
      loginBtn: 'Sign In',
      loginError: 'Login failed',
      logout: 'Sign Out',
      nav_approvals: 'Approvals',
      nav_customers: 'Customers',
      nav_catalog: 'Catalog',
      nav_quotes: 'Quotes',
      nav_tickets: 'Tickets',
      nav_analytics: 'Analytics',
      nav_audit: 'Audit Log',
      nav_templates: 'Templates',
      nav_router: 'Router',
      emptyState: 'No data',
      loading: 'Loading...',
      search: 'Search...',
      approve: 'Approve',
      reject: 'Reject',
      edit: 'Edit',
      save: 'Save',
      cancel: 'Cancel',
      reset: 'Reset',
      confirm: 'Confirm',
      status_pending: 'Pending',
      status_approved: 'Approved',
      status_rejected: 'Rejected',
      status_active: 'Active',
      status_inactive: 'Inactive',
      countdown: 'Time Left',
      days: 'Days',
      hours: 'Hours',
      minutes: 'Minutes',
      seconds: 'Seconds',
      customers_title: 'Customer Management',
      catalog_title: 'Catalog Management',
      quotes_title: 'Quotes',
      tickets_title: 'Tickets',
      analytics_title: 'Analytics',
      audit_title: 'Audit Log',
      templates_title: 'Template Management',
      approvals_title: 'Approval Requests',
      router_title: 'Router',
      router_desc: 'Manage routing rules for customers and sales',
      openRouter: 'Open Router Dashboard',
      importBtn: 'Import CSV',
      importReport: 'Import Report',
      totalCustomers: 'Total Customers',
      totalProducts: 'Total Products',
      totalQuotes: 'Total Quotes',
      totalTickets: 'Total Tickets',
      revenue: 'Revenue',
      pending: 'Pending',
      activeCount: 'Active',
      closed: 'Closed',
      name: 'Name',
      phone: 'Phone',
      email: 'Email',
      company: 'Company',
      source: 'Source',
      date: 'Date',
      amount: 'Amount',
      status: 'Status',
      priority: 'Priority',
      subject: 'Subject',
      message: 'Message',
      customer: 'Customer',
      actions: 'Actions',
      id: 'ID',
      product: 'Product',
      price: 'Price',
      category: 'Category',
      unit: 'Unit',
      description: 'Description',
      notes: 'Notes',
      decision: 'Decision',
      quoteNumber: 'Quote #',
      total: 'Total',
      details: 'Details',
      items: 'Items',
      createdAt: 'Created',
      updatedAt: 'Updated',
      high: 'High',
      medium: 'Medium',
      low: 'Low',
      templateKey: 'Template Key',
      templateLang: 'Language',
      templateBody: 'Body',
      templateActive: 'Active',
      yes: 'Yes',
      no: 'No',
      analytics_query: 'Custom Query',
      runQuery: 'Run Query',
      queryResult: 'Query Results',
      selectTemplate: 'Select Template',
      overview: 'Overview',
      chart_topProducts: 'Top Products',
      chart_sources: 'Customer Sources',
      chart_monthly: 'Monthly Sales',
      sparks_last7: 'Last 7 Days',
      imported: 'Imported',
      skipped: 'Skipped',
      errors: 'Errors',
      row: 'Row',
      errorRow: 'Error',
      editApprovalTitle: 'Edit Approval',
      originalText: 'Original Text',
      editedText: 'Edited Text',
      approvalNote: 'Decision Note',
      closeModal: 'Close',
      sessionExpired: 'Session Expired',
      networkError: 'Network Error',
      noResults: 'No results',
      totalRevenue: 'Total Revenue',
      avgQuote: 'Avg Quote Value',
      conversionRate: 'Conversion Rate',
      topProducts: 'Top Products',
      sourcesBreakdown: 'Sources Breakdown',
      monthlySales: 'Monthly Sales',
      recentActivity: 'Recent Activity',
      all: 'All',
      today: 'Today',
      thisWeek: 'This Week',
      thisMonth: 'This Month',
      noTemplates: 'No templates found',
      saved: 'Saved',
      templateSaved: 'Template saved',
      templateReset: 'Template reset',
      productAdded: 'Product added',
      productUpdated: 'Product updated',
      productToggled: 'Product status toggled',
      csvImportSuccess: 'CSV imported successfully',
      csvImportPartial: 'Import completed with some errors',
      csvImportFailed: 'Import failed',
      confirmApprove: 'Approve this request?',
      confirmReject: 'Reject this request?',
      pendingApprovals: 'Pending approvals',
      productForm: 'Product Form',
      productFormEdit: 'Edit Product',
      productFormAdd: 'Add New Product',
      noData: 'No data available',
      selectFile: 'Select CSV File',
      importPreview: 'Import Preview',
      headerRow: 'Header Row',
      dataRows: 'Data Rows',
      uploaded: 'Uploaded',
      templateQuery: 'Template Query',
      params: 'Parameters',
      enterParams: 'Enter parameters as JSON',
      queryTemplate: 'Query Template',
      noQueries: 'No queries available',
      run: 'Run',
      result: 'Result',
      queue: 'Queue',
      connected: 'Connected',
      disconnected: 'Disconnected',
      streamError: 'Stream connection error',
      barChart: 'Bar Chart',
      sparkline: 'Sparkline'
    }
  };

  /* ---------------------------------------------------------
     2. VIEWS
     --------------------------------------------------------- */
  const VIEWS = [
    'approvals', 'customers', 'catalog', 'quotes', 'tickets',
    'analytics', 'audit', 'templates', 'router'
  ];

  /* ---------------------------------------------------------
     3. STATE
     --------------------------------------------------------- */
  const State = {
    lang: (localStorage.getItem('pa_lang') === 'ar' ? 'en' : (localStorage.getItem('pa_lang') || 'en')),
    admin: null,
    queue: [],
    view: 'approvals',
    source: null,
    timers: {},
    eventSource: null,
    streamRetries: 0,
    maxRetries: 10,
    analyticsCache: null,
    templatesCache: null,
    modalStack: [],
    searchTerms: {},
    csvData: null,
    editingProduct: null,
    editingApproval: null
  };

  /* ---------------------------------------------------------
     4. HELPERS
     --------------------------------------------------------- */
  function t(key) {
    return (I18N[State.lang] && I18N[State.lang][key]) || key;
  }

  function $(sel, ctx) {
    return (ctx || document).querySelector(sel);
  }

  function $$(sel, ctx) {
    return Array.from((ctx || document).querySelectorAll(sel));
  }

  function el(tag) {
    var attrs = arguments.length > 1 && arguments[1] !== undefined ? arguments[1] : {};
    var e = document.createElement(tag);
    Object.keys(attrs).forEach(function (k) {
      if (k === 'className') {
        e.className = attrs[k];
      } else if (k === 'dataset') {
        Object.keys(attrs[k]).forEach(function (dk) {
          e.dataset[dk] = attrs[k][dk];
        });
      } else if (k.indexOf('on') === 0) {
        e.addEventListener(k.slice(2).toLowerCase(), attrs[k]);
      } else if (k === 'html') {
        e.innerHTML = attrs[k];
      } else if (k === 'text') {
        e.textContent = attrs[k];
      } else {
        e.setAttribute(k, attrs[k]);
      }
    });
    for (var i = 2; i < arguments.length; i++) {
      var child = arguments[i];
      if (child == null) continue;
      if (typeof child === 'string' || typeof child === 'number') {
        e.appendChild(document.createTextNode(child));
      } else if (child instanceof Node) {
        e.appendChild(child);
      } else if (Array.isArray(child)) {
        child.forEach(function (c) {
          if (c instanceof Node) e.appendChild(c);
        });
      }
    }
    return e;
  }

  function fmtTime(ms) {
    if (!ms || ms < 0) return '00:00';
    var totalSec = Math.floor(ms / 1000);
    var h = Math.floor(totalSec / 3600);
    var m = Math.floor((totalSec % 3600) / 60);
    var s = totalSec % 60;
    return (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function fmtNum(n) {
    if (n == null) return '0';
    if (typeof n === 'string') n = parseFloat(n);
    if (isNaN(n)) return '0';
    return n.toLocaleString(State.lang === 'ar' ? 'ar-SA' : 'en-US');
  }

  function fmtCurrency(n) {
    if (n == null) return '0';
    return fmtNum(n) + ' SAR';
  }

  function fmtDate(d) {
    if (!d) return '-';
    var date = new Date(d);
    if (isNaN(date.getTime())) return '-';
    return date.toLocaleDateString(State.lang === 'ar' ? 'ar-SA' : 'en-US', {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit'
    });
  }

  function toast(msg, type) {
    type = type || 'info';
    var existing = $('.pa-toast');
    if (existing) existing.remove();
    var colors = {
      success: '#22c55e', error: '#ef4444', info: '#3b82f6', warning: '#f59e0b'
    };
    var icons = {
      success: '&#10003;', error: '&#10007;', info: '&#8505;', warning: '&#9888;'
    };
    var t = el('div', {
      className: 'pa-toast',
      html: '<span style="margin-inline-start:8px;font-size:18px;">' + (icons[type] || icons.info) + '</span><span>' + msg + '</span>'
    });
    t.style.cssText = 'position:fixed;top:20px;' + (State.lang === 'ar' ? 'right' : 'left') + ':20px;z-index:10000;background:' +
      (colors[type] || colors.info) + ';color:#fff;padding:12px 20px;border-radius:8px;font-size:14px;display:flex;align-items:center;' +
      'box-shadow:0 4px 12px rgba(0,0,0,0.15);animation:paSlideIn .3s ease;font-family:inherit;max-width:400px;';
    document.body.appendChild(t);
    setTimeout(function () {
      t.style.opacity = '0';
      t.style.transform = 'translateY(-10px)';
      t.style.transition = 'all .3s ease';
      setTimeout(function () { if (t.parentNode) t.remove(); }, 300);
    }, 3000);
  }

  function debounce(fn, delay) {
    var timer;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () { fn.apply(ctx, args); }, delay);
    };
  }

  function escHtml(s) {
    if (!s) return '';
    var d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  function emptyState(msg) {
    return el('div', {
      style: 'text-align:center;padding:60px 20px;color:#94a3b8;font-size:16px;'
    }, msg || t('emptyState'));
  }

  function spinner() {
    return el('div', {
      style: 'display:flex;justify-content:center;padding:60px 20px;'
    }, el('div', {
      className: 'pa-spinner',
      style: 'width:36px;height:36px;border:3px solid #e2e8f0;border-top-color:#3b82f6;border-radius:50%;animation:paSpin .8s linear infinite;'
    }));
  }

  /* ---------------------------------------------------------
     5. API
     --------------------------------------------------------- */
  async function api(path, options) {
    options = options || {};
    var headers = options.headers || {};
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }
    try {
      var resp = await fetch('/admin/api' + path, {
        method: options.method || 'GET',
        headers: headers,
        body: options.body instanceof FormData ? options.body :
          (options.body ? JSON.stringify(options.body) : undefined),
        credentials: 'same-origin'
      });
      if (resp.status === 401) {
        State.admin = null;
        stopStream();
        renderLogin();
        toast(t('sessionExpired'), 'error');
        return null;
      }
      if (!resp.ok) {
        var errText;
        try {
          var errJson = await resp.json();
          errText = errJson.error || errJson.message || resp.statusText;
        } catch (e) {
          errText = resp.statusText;
        }
        throw new Error(errText);
      }
      var contentType = resp.headers.get('content-type') || '';
      if (contentType.indexOf('application/json') !== -1) {
        return await resp.json();
      }
      return await resp.text();
    } catch (err) {
      if (err.message !== 'Failed to fetch') {
        toast(err.message, 'error');
      } else {
        toast(t('networkError'), 'error');
      }
      throw err;
    }
  }

  /* ---------------------------------------------------------
     6. AUTH: login / logout / enter
     --------------------------------------------------------- */
  function renderLogin() {
    stopStream();
    var app = $('#app');
    app.innerHTML = '';
    app.dir = I18N[State.lang].dir;
    var card = el('div', {
      className: 'pa-login-card',
      style: 'background:#fff;border-radius:16px;padding:40px;max-width:400px;margin:80px auto;box-shadow:0 4px 24px rgba(0,0,0,.08);text-align:center;'
    });
    var langBtn = el('button', {
      className: 'pa-lang-toggle',
      style: 'position:fixed;top:16px;' + (State.lang === 'ar' ? 'left' : 'right') + ':16px;background:#f1f5f9;border:none;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:14px;font-family:inherit;z-index:100;',
      onClick: function () {
        State.lang = State.lang === 'ar' ? 'en' : 'ar';
        localStorage.setItem('pa_lang', State.lang);
        renderLogin();
      }
    }, t('langLabel'));

    var form = el('form', { className: 'pa-login-form' });
    form.addEventListener('submit', function(e) { e.preventDefault(); handleLogin(e); });

    var title = el('h1', {
      style: 'margin:0 0 4px;font-size:24px;color:#1e293b;font-weight:700;'
    }, t('loginTitle'));
    var subtitle = el('p', {
      style: 'margin:0 0 24px;color:#64748b;font-size:14px;'
    }, t('loginSubtitle'));

    var userInput = el('input', {
      type: 'text', name: 'username', placeholder: t('username'), required: 'required',
      style: 'width:100%;padding:12px 16px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px;margin-bottom:12px;box-sizing:border-box;font-family:inherit;outline:none;transition:border .2s;',
      autocomplete: 'username'
    });
    var passInput = el('input', {
      type: 'password', name: 'password', placeholder: t('password'), required: 'required',
      style: 'width:100%;padding:12px 16px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px;margin-bottom:16px;box-sizing:border-box;font-family:inherit;outline:none;transition:border .2s;',
      autocomplete: 'current-password'
    });
    var loginBtn = el('button', {
      type: 'submit',
      style: 'width:100%;padding:12px;background:#3b82f6;color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;transition:background .2s;font-family:inherit;'
    }, t('loginBtn'));

    var errorDiv = el('div', {
      className: 'pa-login-error',
      style: 'color:#ef4444;font-size:13px;margin-top:8px;display:none;'
    });

    userInput.addEventListener('focus', function () { userInput.style.borderColor = '#3b82f6'; });
    userInput.addEventListener('blur', function () { userInput.style.borderColor = '#e2e8f0'; });
    passInput.addEventListener('focus', function () { passInput.style.borderColor = '#3b82f6'; });
    passInput.addEventListener('blur', function () { passInput.style.borderColor = '#e2e8f0'; });
    loginBtn.addEventListener('mouseenter', function () { loginBtn.style.background = '#2563eb'; });
    loginBtn.addEventListener('mouseleave', function () { loginBtn.style.background = '#3b82f6'; });

    form.appendChild(title);
    form.appendChild(subtitle);
    form.appendChild(userInput);
    form.appendChild(passInput);
    form.appendChild(loginBtn);
    form.appendChild(errorDiv);
    card.appendChild(form);
    app.appendChild(langBtn);
    app.appendChild(card);

    setTimeout(function () { userInput.focus(); }, 100);
  }

  async function handleLogin(e) {
    e.preventDefault();
    var form = e.target;
    var username = form.querySelector('[name=username]').value.trim();
    var password = form.querySelector('[name=password]').value;
    var loginBtn = form.querySelector('button[type=submit]');
    var errorDiv = form.querySelector('.pa-login-error');

    loginBtn.disabled = true;
    loginBtn.textContent = t('loading');
    errorDiv.style.display = 'none';

    try {
      var res = await api('/auth/login', {
        method: 'POST',
        body: { username: username, password: password }
      });
      if (res && res.admin) {
        State.admin = res.admin;
        enterDashboard();
      } else {
        errorDiv.textContent = t('loginError');
        errorDiv.style.display = 'block';
        loginBtn.disabled = false;
        loginBtn.textContent = t('loginBtn');
      }
    } catch (err) {
      errorDiv.textContent = t('loginError');
      errorDiv.style.display = 'block';
      loginBtn.disabled = false;
      loginBtn.textContent = t('loginBtn');
    }
  }

  async function handleLogout() {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch (e) { /* ignore */ }
    State.admin = null;
    stopStream();
    renderLogin();
  }

  async function checkSession() {
    try {
      var res = await api('/auth/session');
      if (res && res.admin) {
        State.admin = res.admin;
        enterDashboard();
      } else {
        renderLogin();
      }
    } catch (e) {
      renderLogin();
    }
  }

  function enterDashboard() {
    renderAppShell();
    applyI18n();
    var hash = window.location.hash.replace('#', '').replace('/', '');
    if (VIEWS.indexOf(hash) !== -1) {
      State.view = hash;
    } else {
      State.view = 'approvals';
    }
    navigate(State.view);
    startStream();
  }

  /* ---------------------------------------------------------
     7. APP SHELL, NAV, NAVIGATE, APPLY I18N
     --------------------------------------------------------- */
  function renderAppShell() {
    var app = $('#app');
    app.innerHTML = '';
    app.dir = I18N[State.lang].dir;

    var topbar = el('div', {
      className: 'pa-topbar',
      style: 'display:flex;align-items:center;justify-content:space-between;padding:0 24px;height:60px;background:#fff;border-bottom:1px solid #e2e8f0;position:sticky;top:0;z-index:1000;'
    });

    var brandArea = el('div', { style: 'display:flex;align-items:center;gap:12px;' });
    var logo = el('div', {
      style: 'width:36px;height:36px;background:#3b82f6;border-radius:10px;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:16px;'
    }, 'PA');
    var brand = el('span', {
      style: 'font-weight:700;font-size:16px;color:#1e293b;'
    }, 'Kia-Agent');
    brandArea.appendChild(logo);
    brandArea.appendChild(brand);

    var topRight = el('div', { style: 'display:flex;align-items:center;gap:12px;' });
    var streamDot = el('span', {
      className: 'pa-stream-dot',
      style: 'width:8px;height:8px;border-radius:50%;background:#94a3b8;display:inline-block;',
      title: t('disconnected')
    });
    var queueBadge = el('span', {
      className: 'pa-queue-badge',
      style: 'background:#fee2e2;color:#dc2626;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600;display:none;'
    }, '0');
    var adminName = el('span', {
      className: 'pa-admin-name',
      style: 'font-size:13px;color:#64748b;'
    }, State.admin ? (State.admin.name || State.admin.username || '') : '');

    var langBtn = el('button', {
      className: 'pa-lang-btn',
      style: 'background:#f1f5f9;border:1px solid #e2e8f0;padding:6px 12px;border-radius:8px;cursor:pointer;font-size:13px;font-family:inherit;',
      onClick: function () {
        State.lang = State.lang === 'ar' ? 'en' : 'ar';
        localStorage.setItem('pa_lang', State.lang);
        applyI18n();
        navigate(State.view);
      }
    }, t('langLabel'));

    var logoutBtn = el('button', {
      className: 'pa-logout-btn',
      style: 'background:none;border:1px solid #e2e8f0;padding:6px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:#64748b;font-family:inherit;transition:all .2s;',
      onClick: handleLogout
    }, t('logout'));

    topRight.appendChild(streamDot);
    topRight.appendChild(queueBadge);
    topRight.appendChild(adminName);
    topRight.appendChild(langBtn);
    topRight.appendChild(logoutBtn);
    topbar.appendChild(brandArea);
    topbar.appendChild(topRight);

    var nav = el('nav', {
      className: 'pa-nav',
      style: 'display:flex;gap:4px;padding:8px 24px;background:#fff;border-bottom:1px solid #e2e8f0;overflow-x:auto;'
    });
    VIEWS.forEach(function (view) {
      var btn = el('button', {
        className: 'pa-nav-btn',
        dataset: { view: view },
        style: 'padding:8px 16px;border:none;background:none;border-radius:8px;cursor:pointer;font-size:13px;font-family:inherit;color:#64748b;transition:all .2s;white-space:nowrap;',
        onClick: function () { navigate(view); }
      }, t('nav_' + view));
      nav.appendChild(btn);
    });

    var main = el('main', {
      id: 'main-content',
      className: 'pa-main',
      style: 'padding:24px;min-height:calc(100vh - 120px);'
    });

    var modalContainer = el('div', { id: 'modal-container' });

    app.appendChild(topbar);
    app.appendChild(nav);
    app.appendChild(main);
    app.appendChild(modalContainer);

    injectStyles();
  }

  function injectStyles() {
    if ($('#pa-dynamic-styles')) return;
    var style = document.createElement('style');
    style.id = 'pa-dynamic-styles';
    style.textContent = '\n' +
      '@keyframes paSpin { to { transform: rotate(360deg); } }\n' +
      '@keyframes paSlideIn { from { opacity:0; transform:translateY(-10px); } to { opacity:1; transform:translateY(0); } }\n' +
      '@keyframes paFadeIn { from { opacity:0; } to { opacity:1; } }\n' +
      '@keyframes paPulse { 0%,100% { opacity:1; } 50% { opacity:.5; } }\n' +
      '.pa-nav-btn.active { background:#eff6ff !important; color:#3b82f6 !important; font-weight:600; }\n' +
      '.pa-nav-btn:hover { background:#f8fafc; color:#1e293b; }\n' +
      '.pa-card { background:#fff;border-radius:12px;border:1px solid #e2e8f0;padding:20px;margin-bottom:16px;transition:box-shadow .2s; }\n' +
      '.pa-card:hover { box-shadow:0 2px 12px rgba(0,0,0,.06); }\n' +
      '.pa-btn { padding:8px 16px;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:500;font-family:inherit;transition:all .2s;display:inline-flex;align-items:center;gap:6px; }\n' +
      '.pa-btn-primary { background:#3b82f6;color:#fff; }\n' +
      '.pa-btn-primary:hover { background:#2563eb; }\n' +
      '.pa-btn-success { background:#22c55e;color:#fff; }\n' +
      '.pa-btn-success:hover { background:#16a34a; }\n' +
      '.pa-btn-danger { background:#ef4444;color:#fff; }\n' +
      '.pa-btn-danger:hover { background:#dc2626; }\n' +
      '.pa-btn-warning { background:#f59e0b;color:#fff; }\n' +
      '.pa-btn-warning:hover { background:#d97706; }\n' +
      '.pa-btn-ghost { background:#f1f5f9;color:#475569; }\n' +
      '.pa-btn-ghost:hover { background:#e2e8f0; }\n' +
      '.pa-btn-outline { background:transparent;border:1.5px solid #e2e8f0;color:#475569; }\n' +
      '.pa-btn-outline:hover { background:#f8fafc;border-color:#cbd5e1; }\n' +
      '.pa-btn:disabled { opacity:.5;cursor:not-allowed; }\n' +
      '.pa-table { width:100%;border-collapse:collapse;font-size:13px; }\n' +
      '.pa-table th { background:#f8fafc;padding:10px 12px;text-align:' + (State.lang === 'ar' ? 'right' : 'left') + ';font-weight:600;color:#475569;border-bottom:2px solid #e2e8f0;white-space:nowrap; }\n' +
      '.pa-table td { padding:10px 12px;border-bottom:1px solid #f1f5f9;color:#334155; }\n' +
      '.pa-table tr:hover td { background:#f8fafc; }\n' +
      '.pa-badge { display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:600; }\n' +
      '.pa-badge-pending { background:#fef3c7;color:#92400e; }\n' +
      '.pa-badge-approved { background:#dcfce7;color:#166534; }\n' +
      '.pa-badge-rejected { background:#fee2e2;color:#991b1b; }\n' +
      '.pa-badge-active { background:#dcfce7;color:#166534; }\n' +
      '.pa-badge-inactive { background:#f1f5f9;color:#64748b; }\n' +
      '.pa-badge-high { background:#fee2e2;color:#991b1b; }\n' +
      '.pa-badge-medium { background:#fef3c7;color:#92400e; }\n' +
      '.pa-badge-low { background:#dbeafe;color:#1e40af; }\n' +
      '.pa-stat-card { background:#fff;border-radius:12px;border:1px solid #e2e8f0;padding:20px;text-align:center; }\n' +
      '.pa-stat-value { font-size:28px;font-weight:700;color:#1e293b;margin:8px 0 4px; }\n' +
      '.pa-stat-label { font-size:13px;color:#64748b; }\n' +
      '.pa-stat-icon { font-size:24px;margin-bottom:8px; }\n' +
      '.pa-search { width:100%;padding:10px 16px;border:1.5px solid #e2e8f0;border-radius:10px;font-size:14px;font-family:inherit;outline:none;transition:border .2s;box-sizing:border-box; }\n' +
      '.pa-search:focus { border-color:#3b82f6; }\n' +
      '.pa-modal-overlay { position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,.4);z-index:5000;display:flex;align-items:center;justify-content:center;animation:paFadeIn .2s ease;padding:20px; }\n' +
      '.pa-modal { background:#fff;border-radius:16px;max-width:600px;width:100%;max-height:80vh;overflow-y:auto;padding:24px;box-shadow:0 8px 32px rgba(0,0,0,.12); }\n' +
      '.pa-modal-header { display:flex;justify-content:space-between;align-items:center;margin-bottom:16px; }\n' +
      '.pa-modal-title { font-size:18px;font-weight:700;color:#1e293b; }\n' +
      '.pa-modal-close { background:none;border:none;font-size:24px;cursor:pointer;color:#94a3b8;padding:4px 8px;border-radius:6px; }\n' +
      '.pa-modal-close:hover { background:#f1f5f9;color:#475569; }\n' +
      '.pa-form-group { margin-bottom:16px; }\n' +
      '.pa-form-label { display:block;font-size:13px;font-weight:600;color:#475569;margin-bottom:6px; }\n' +
      '.pa-form-input { width:100%;padding:10px 14px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:14px;font-family:inherit;outline:none;box-sizing:border-box;transition:border .2s; }\n' +
      '.pa-form-input:focus { border-color:#3b82f6; }\n' +
      '.pa-form-textarea { width:100%;padding:10px 14px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:14px;font-family:inherit;outline:none;box-sizing:border-box;min-height:100px;resize:vertical;transition:border .2s; }\n' +
      '.pa-form-textarea:focus { border-color:#3b82f6; }\n' +
      '.pa-form-select { width:100%;padding:10px 14px;border:1.5px solid #e2e8f0;border-radius:8px;font-size:14px;font-family:inherit;background:#fff;outline:none;box-sizing:border-box; }\n' +
      '.pa-bar { display:flex;align-items:flex-end;gap:4px;height:120px;padding:8px 0; }\n' +
      '.pa-bar-col { flex:1;display:flex;flex-direction:column;align-items:center;gap:4px; }\n' +
      '.pa-bar-rect { width:100%;border-radius:4px 4px 0 0;background:#3b82f6;transition:height .3s ease;min-height:2px; }\n' +
      '.pa-bar-label { font-size:10px;color:#94a3b8;text-align:center;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:60px; }\n' +
      '.pa-bar-value { font-size:10px;color:#475569;font-weight:600; }\n' +
      '.pa-sparkline { display:flex;align-items:flex-end;gap:2px;height:40px; }\n' +
      '.pa-spark-bar { flex:1;border-radius:2px;background:#3b82f6;min-height:2px;transition:height .3s; }\n' +
      '.pa-timer { font-variant-numeric:tabular-nums;font-family:monospace;font-size:14px;font-weight:600;color:#dc2626; }\n' +
      '.pa-empty { text-align:center;padding:60px 20px;color:#94a3b8; }\n' +
      '.pa-section-title { font-size:18px;font-weight:700;color:#1e293b;margin-bottom:16px; }\n' +
      '.pa-grid-2 { display:grid;grid-template-columns:1fr 1fr;gap:16px; }\n' +
      '.pa-grid-3 { display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px; }\n' +
      '.pa-grid-4 { display:grid;grid-template-columns:repeat(4,1fr);gap:16px; }\n' +
      '.pa-toolbar { display:flex;gap:12px;align-items:center;margin-bottom:16px;flex-wrap:wrap; }\n' +
      '.pa-countdown-ring { display:inline-flex;align-items:center;gap:8px;padding:4px 12px;background:#fef2f2;border-radius:8px;border:1px solid #fecaca; }\n' +
      '@media (max-width:768px) { .pa-grid-4 { grid-template-columns:1fr 1fr; } .pa-grid-3 { grid-template-columns:1fr; } .pa-grid-2 { grid-template-columns:1fr; } }\n' +
      '\n';
    document.head.appendChild(style);
  }

  function renderNav() {
    $$('.pa-nav-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.view === State.view);
    });
  }

  function navigate(view) {
    if (VIEWS.indexOf(view) === -1) view = 'approvals';
    State.view = view;
    window.location.hash = '#' + view;
    renderNav();
    var main = $('#main-content');
    if (!main) return;
    main.innerHTML = '';
    main.appendChild(spinner());
    var renderer = RENDERERS[view];
    if (renderer) {
      renderer(main).catch(function (err) {
        main.innerHTML = '';
        main.appendChild(el('div', { className: 'pa-empty' }, t('emptyState')));
        console.error('Render error:', view, err);
      });
    }
  }

  function applyI18n() {
    var app = $('#app');
    if (app) app.dir = I18N[State.lang].dir;
    document.documentElement.dir = I18N[State.lang].dir;
    document.documentElement.lang = State.lang;
  }

  /* ---------------------------------------------------------
     8. SSE: stream
     --------------------------------------------------------- */
  function startStream() {
    stopStream();
    State.streamRetries = 0;
    connectStream();
  }

  function connectStream() {
    if (State.eventSource) {
      State.eventSource.close();
      State.eventSource = null;
    }
    try {
      var es = new EventSource('/admin/api/stream');
      State.eventSource = es;
      es.onopen = function () {
        State.streamRetries = 0;
        updateStreamDot(true);
      };
      es.onmessage = function (e) {
        try {
          var data = JSON.parse(e.data);
          handleStreamEvent(data);
        } catch (err) {
          console.error('SSE parse error:', err);
        }
      };
      es.addEventListener('queue', function (e) {
        try {
          var data = JSON.parse(e.data);
          setQueue(data.items || data);
        } catch (err) { /* ignore */ }
      });
      es.addEventListener('approval', function (e) {
        try {
          var data = JSON.parse(e.data);
          if (State.view === 'approvals') refreshQueue();
        } catch (err) { /* ignore */ }
      });
      es.addEventListener('ticket', function (e) {
        if (State.view === 'tickets') navigate('tickets');
      });
      es.addEventListener('quote', function (e) {
        if (State.view === 'quotes') navigate('quotes');
      });
      es.onerror = function () {
        updateStreamDot(false);
        es.close();
        State.eventSource = null;
        if (State.streamRetries < State.maxRetries) {
          State.streamRetries++;
          var delay = Math.min(1000 * Math.pow(2, State.streamRetries), 30000);
          setTimeout(connectStream, delay);
        }
      };
    } catch (err) {
      console.error('SSE connection error:', err);
      updateStreamDot(false);
    }
  }

  function stopStream() {
    if (State.eventSource) {
      State.eventSource.close();
      State.eventSource = null;
    }
    updateStreamDot(false);
    Object.keys(State.timers).forEach(function (k) {
      clearInterval(State.timers[k]);
      clearTimeout(State.timers[k]);
    });
    State.timers = {};
  }

  function updateStreamDot(connected) {
    var dot = $('.pa-stream-dot');
    if (dot) {
      dot.style.background = connected ? '#22c55e' : '#94a3b8';
      dot.title = connected ? t('connected') : t('disconnected');
    }
  }

  function handleStreamEvent(data) {
    if (!data) return;
    if (data.type === 'queue_update' || data.type === 'approval_new' || data.type === 'approval_update') {
      refreshQueue();
    }
  }

  function refreshQueue() {
    api('/approvals?limit=100').then(function (res) {
      if (res && res.items) setQueue(res.items);
    }).catch(function () { });
  }

  function setQueue(items) {
    State.queue = Array.isArray(items) ? items : [];
    var badge = $('.pa-queue-badge');
    if (badge) {
      var pendingCount = State.queue.filter(function (i) {
        return i.status === 'pending';
      }).length;
      if (pendingCount > 0) {
        badge.textContent = pendingCount;
        badge.style.display = 'inline-block';
      } else {
        badge.style.display = 'none';
      }
    }
  }

  /* ---------------------------------------------------------
     9. RENDERERS
     --------------------------------------------------------- */
  var RENDERERS = {};

    /* ---- APPROVALS ---- */
    RENDERERS.approvals = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('approvals_title'));
      var refreshBtn = el('button', {
        className: 'pa-btn pa-btn-ghost',
        onClick: function () { navigate('approvals'); }
      }, '&#8635; ' + t('loading').replace('...', ''));
      header.appendChild(title);
      header.appendChild(refreshBtn);
      container.appendChild(header);

      try {
        var res = await api('/approvals?limit=100');
        var items = (res && res.items) ? res.items : [];
        setQueue(items);

        if (items.length === 0) {
          container.appendChild(emptyState(t('emptyState')));
          return;
        }

        var grid = el('div', { className: 'pa-grid-2' });
        items.forEach(function (item) {
          var card = createApprovalCard(item);
          grid.appendChild(card);
        });
        container.appendChild(grid);
        startCountdowns();
      } catch (err) {
        container.appendChild(emptyState(t('networkError')));
      }
    };

    function createApprovalCard(item) {
      var statusClass = 'pa-badge-' + (item.status || 'pending');
      var card = el('div', { className: 'pa-card' });

      var headerRow = el('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;' });
      var idSpan = el('span', { style: 'font-size:12px;color:#94a3b8;' }, '#' + (item.id || item._id || '').toString().slice(-6));
      var statusBadge = el('span', {
        className: 'pa-badge ' + statusClass,
      }, t('status_' + (item.status || 'pending')));
      headerRow.appendChild(idSpan);
      headerRow.appendChild(statusBadge);

      var source = el('div', { style: 'font-size:12px;color:#64748b;margin-bottom:8px;' },
        (item.source ? item.source + ' | ' : '') + (item.channel || '') + (item.customer_name ? ' | ' + item.customer_name : '')
      );

      var text = el('div', {
        style: 'font-size:14px;color:#1e293b;line-height:1.6;margin-bottom:12px;white-space:pre-wrap;max-height:120px;overflow-y:auto;',
        html: escHtml(item.text || item.body || item.content || item.original_text || '')
      });

      var timerRow = el('div', { style: 'display:flex;align-items:center;gap:8px;margin-bottom:12px;' });
      var timerLabel = el('span', { style: 'font-size:12px;color:#64748b;' }, t('countdown') + ':');
      var timerVal = el('span', { className: 'pa-timer pa-countdown-value', style: 'font-size:14px;' });

      if (item.expires_at) {
        timerVal.dataset.expires = item.expires_at;
        timerVal.dataset.id = item.id || item._id;
      } else if (item.ttl_hours) {
        var exp = new Date(item.created_at || item.createdAt);
        exp.setHours(exp.getHours() + (item.ttl_hours || 24));
        timerVal.dataset.expires = exp.toISOString();
        timerVal.dataset.id = item.id || item._id;
      }
      timerRow.appendChild(timerLabel);
      timerRow.appendChild(timerVal);

      var btnRow = el('div', { style: 'display:flex;gap:8px;flex-wrap:wrap;' });

      if (item.status === 'pending') {
        var approveBtn = el('button', {
          className: 'pa-btn pa-btn-success',
          onClick: function () { decide(item.id || item._id, 'approved'); }
        }, t('approve'));
        var rejectBtn = el('button', {
          className: 'pa-btn pa-btn-danger',
          onClick: function () { decide(item.id || item._id, 'rejected'); }
        }, t('reject'));
        var editBtn = el('button', {
          className: 'pa-btn pa-btn-warning',
          onClick: function () { openEdit(item); }
        }, t('edit'));
        btnRow.appendChild(approveBtn);
        btnRow.appendChild(rejectBtn);
        btnRow.appendChild(editBtn);
      }

      card.appendChild(headerRow);
      card.appendChild(source);
      card.appendChild(text);
      if (item.status === 'pending') {
        card.appendChild(timerRow);
      }
      card.appendChild(btnRow);
      return card;
    }

    function startCountdowns() {
      Object.keys(State.timers).forEach(function (k) {
        if (k.indexOf('countdown_') === 0) clearInterval(State.timers[k]);
      });
      $$('.pa-countdown-value').forEach(function (span) {
        var expires = span.dataset.expires;
        var id = span.dataset.id;
        if (!expires) { span.textContent = '-'; return; }
        function tick() {
          var diff = new Date(expires).getTime() - Date.now();
          if (diff <= 0) {
            span.textContent = '00:00:00';
            span.style.color = '#94a3b8';
            clearInterval(State.timers['countdown_' + id]);
            return;
          }
          var d = Math.floor(diff / 86400000);
          var h = Math.floor((diff % 86400000) / 3600000);
          var m = Math.floor((diff % 3600000) / 60000);
          var s = Math.floor((diff % 60000) / 1000);
          var text = '';
          if (d > 0) text += d + t('days') + ' ';
          text += (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
          span.textContent = text;
        }
        tick();
        State.timers['countdown_' + id] = setInterval(tick, 1000);
      });
    }

    /* ---- CUSTOMERS ---- */
    RENDERERS.customers = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('customers_title'));
      var searchInput = el('input', {
        className: 'pa-search',
        placeholder: t('search'),
        style: 'max-width:300px;',
        onInput: debounce(function () { loadCustomers(container, searchInput.value); }, 400)
      });
      header.appendChild(title);
      header.appendChild(searchInput);
      container.appendChild(header);

      var tableWrap = el('div', { className: 'pa-card', id: 'customers-table-wrap' });
      tableWrap.appendChild(spinner());
      container.appendChild(tableWrap);
      loadCustomers(container, '');
    };

    async function loadCustomers(container, query) {
      var wrap = $('#customers-table-wrap') || container;
      wrap.innerHTML = '';
      wrap.appendChild(spinner());
      try {
        var res = await api('/customers?q=' + encodeURIComponent(query));
        var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        wrap.innerHTML = '';
        if (items.length === 0) {
          wrap.appendChild(emptyState(t('noResults')));
          return;
        }
        var table = el('table', { className: 'pa-table' });
        var thead = el('thead');
        var headerRow = el('tr');
        [t('id'), t('name'), t('phone'), t('email'), t('company'), t('source'), t('date')].forEach(function (h) {
          headerRow.appendChild(el('th', {}, h));
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        var tbody = el('tbody');
        items.forEach(function (c) {
          var row = el('tr');
          var shortId = (c.id || c._id || '').toString().slice(-6);
          row.appendChild(el('td', {}, shortId));
          row.appendChild(el('td', {}, c.name || c.full_name || '-'));
          row.appendChild(el('td', {}, c.phone || c.mobile || '-'));
          row.appendChild(el('td', {}, c.email || '-'));
          row.appendChild(el('td', {}, c.company || c.organization || '-'));
          row.appendChild(el('td', {}, c.source || '-'));
          row.appendChild(el('td', {}, fmtDate(c.created_at || c.createdAt)));
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        wrap.appendChild(table);
      } catch (err) {
        wrap.appendChild(emptyState(t('networkError')));
      }
    }

    /* ---- CATALOG ---- */
    RENDERERS.catalog = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('catalog_title'));
      var searchInput = el('input', {
        className: 'pa-search',
        placeholder: t('search'),
        style: 'max-width:250px;',
        onInput: debounce(function () { loadProducts(container, searchInput.value); }, 400)
      });
      var addBtn = el('button', {
        className: 'pa-btn pa-btn-primary',
        onClick: function () { openProductForm(null, container); }
      }, '+ ' + t('productFormAdd'));
      var importBtn = el('button', {
        className: 'pa-btn pa-btn-ghost',
        onClick: function () { openImportDialog(container); }
      }, t('importBtn'));
      header.appendChild(title);
      header.appendChild(searchInput);
      header.appendChild(addBtn);
      header.appendChild(importBtn);
      container.appendChild(header);

      var tableWrap = el('div', { className: 'pa-card', id: 'catalog-table-wrap' });
      tableWrap.appendChild(spinner());
      container.appendChild(tableWrap);
      loadProducts(container, '');
    };

    async function loadProducts(container, query) {
      var wrap = $('#catalog-table-wrap') || container;
      wrap.innerHTML = '';
      wrap.appendChild(spinner());
      try {
        var res = await api('/products?q=' + encodeURIComponent(query));
        var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        wrap.innerHTML = '';
        if (items.length === 0) {
          wrap.appendChild(emptyState(t('noResults')));
          return;
        }
        var table = el('table', { className: 'pa-table' });
        var thead = el('thead');
        var headerRow = el('tr');
        [t('id'), t('product'), t('category'), t('price'), t('unit'), t('status'), t('actions')].forEach(function (h) {
          headerRow.appendChild(el('th', {}, h));
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        var tbody = el('tbody');
        items.forEach(function (p) {
          var row = el('tr');
          var shortId = (p.id || p._id || '').toString().slice(-6);
          var isActive = p.active !== false && p.status !== 'inactive';
          row.appendChild(el('td', {}, shortId));
          row.appendChild(el('td', {}, p.name || p.title || '-'));
          row.appendChild(el('td', {}, p.category || '-'));
          row.appendChild(el('td', {}, fmtCurrency(p.price)));
          row.appendChild(el('td', {}, p.unit || '-'));
          row.appendChild(el('td', {}, el('span', {
            className: 'pa-badge ' + (isActive ? 'pa-badge-active' : 'pa-badge-inactive')
          }, isActive ? t('status_active') : t('status_inactive'))));
          var actions = el('td', { style: 'white-space:nowrap;' });
          var editBtn = el('button', {
            className: 'pa-btn pa-btn-ghost',
            style: 'padding:4px 8px;font-size:12px;',
            onClick: function () { openProductForm(p, container); }
          }, t('edit'));
          var toggleBtn = el('button', {
            className: 'pa-btn ' + (isActive ? 'pa-btn-warning' : 'pa-btn-success'),
            style: 'padding:4px 8px;font-size:12px;',
            onClick: function () { toggleProduct(p, !isActive, container); }
          }, isActive ? t('status_inactive') : t('status_active'));
          actions.appendChild(editBtn);
          actions.appendChild(toggleBtn);
          row.appendChild(actions);
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        wrap.appendChild(table);
      } catch (err) {
        wrap.appendChild(emptyState(t('networkError')));
      }
    }

    function openProductForm(product, container) {
      State.editingProduct = product;
      var isEdit = !!product;
      var modal = createModal(isEdit ? t('productFormEdit') : t('productFormAdd'));

      var form = el('form');
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var fd = new FormData(form);
        var data = {};
        fd.forEach(function (v, k) { data[k] = v; });
        if (data.price) data.price = parseFloat(data.price);
        if (data.active !== undefined) data.active = data.active === 'true' || data.active === 'on';

        try {
          if (isEdit) {
            await api('/products/' + (product.id || product._id), { method: 'PUT', body: data });
            toast(t('productUpdated'), 'success');
          } else {
            await api('/products', { method: 'POST', body: data });
            toast(t('productAdded'), 'success');
          }
          closeModal();
          if (container) navigate(State.view);
        } catch (err) {
          toast(err.message, 'error');
        }
      });

      var fields = [
        { name: 'name', label: t('product'), type: 'text', value: product ? product.name || product.title || '' : '' },
        { name: 'category', label: t('category'), type: 'text', value: product ? product.category || '' : '' },
        { name: 'price', label: t('price'), type: 'number', value: product ? product.price || '' : '' },
        { name: 'unit', label: t('unit'), type: 'text', value: product ? product.unit || '' : '' },
        { name: 'description', label: t('description'), type: 'textarea', value: product ? product.description || '' : '' }
      ];

      fields.forEach(function (f) {
        var group = el('div', { className: 'pa-form-group' });
        var label = el('label', { className: 'pa-form-label' }, f.label);
        var input;
        if (f.type === 'textarea') {
          input = el('textarea', { className: 'pa-form-textarea', name: f.name });
        } else {
          input = el('input', { className: 'pa-form-input', type: f.type, name: f.name });
        }
        input.value = f.value;
        group.appendChild(label);
        group.appendChild(input);
        form.appendChild(group);
      });

      var btnRow = el('div', { style: 'display:flex;gap:8px;justify-content:flex-end;margin-top:16px;' });
      var cancelBtn = el('button', {
        className: 'pa-btn pa-btn-ghost',
        type: 'button',
        onClick: closeModal
      }, t('cancel'));
      var saveBtn = el('button', {
        className: 'pa-btn pa-btn-primary',
        type: 'submit'
      }, t('save'));
      btnRow.appendChild(cancelBtn);
      btnRow.appendChild(saveBtn);
      form.appendChild(btnRow);

      modal.querySelector('.pa-modal-body').appendChild(form);
      document.getElementById('modal-container').appendChild(modal);
    }

    async function toggleProduct(product, active, container) {
      try {
        await api('/products/' + (product.id || product._id), {
          method: 'PUT',
          body: { active: active }
        });
        toast(t('productToggled'), 'success');
        if (container) navigate(State.view);
      } catch (err) {
        toast(err.message, 'error');
      }
    }

    function openImportDialog(container) {
      var modal = createModal(t('importBtn'));
      var body = modal.querySelector('.pa-modal-body');

      var fileGroup = el('div', { className: 'pa-form-group' });
      var fileLabel = el('label', { className: 'pa-form-label' }, t('selectFile'));
      var fileInput = el('input', {
        type: 'file',
        accept: '.csv',
        className: 'pa-form-input',
        onChange: function (e) {
          var file = e.target.files[0];
          if (!file) return;
          var reader = new FileReader();
          reader.onload = function (ev) {
            State.csvData = ev.target.result;
            previewCsv(ev.target.result, body);
          };
          reader.readAsText(file);
        }
      });
      fileGroup.appendChild(fileLabel);
      fileGroup.appendChild(fileInput);

      var previewDiv = el('div', { id: 'csv-preview' });
      var btnRow = el('div', { style: 'display:flex;gap:8px;justify-content:flex-end;margin-top:16px;' });
      var cancelBtn = el('button', { className: 'pa-btn pa-btn-ghost', onClick: closeModal }, t('cancel'));
      var importBtn = el('button', {
        className: 'pa-btn pa-btn-primary',
        id: 'csv-import-btn',
        disabled: 'disabled',
        onClick: async function () {
          if (!State.csvData) return;
          importBtn.disabled = true;
          importBtn.textContent = t('loading');
          try {
            var fd = new FormData();
            fd.append('file', new Blob([State.csvData], { type: 'text/csv' }), 'products.csv');
            var res = await api('/products/import', { method: 'POST', body: fd });
            closeModal();
            if (res) openImportReport(res, container);
            toast(t('csvImportSuccess'), 'success');
            navigate(State.view);
          } catch (err) {
            toast(t('csvImportFailed'), 'error');
          }
        }
      }, t('importBtn'));
      btnRow.appendChild(cancelBtn);
      btnRow.appendChild(importBtn);

      body.appendChild(fileGroup);
      body.appendChild(previewDiv);
      body.appendChild(btnRow);
      document.getElementById('modal-container').appendChild(modal);
    }

    function previewCsv(text, container) {
      var preview = container.querySelector('#csv-preview') || container;
      var lines = text.split('\n').filter(function (l) { return l.trim(); });
      var header = lines[0] || '';
      var dataRows = lines.length - 1;
      preview.innerHTML = '';
      var info = el('div', { style: 'font-size:13px;color:#475569;' });
      info.appendChild(el('div', {}, t('headerRow') + ': ' + escHtml(header)));
      info.appendChild(el('div', {}, t('dataRows') + ': ' + dataRows));
      preview.appendChild(info);

      var importBtn = $('#csv-import-btn');
      if (importBtn) importBtn.disabled = false;
    }

    function openImportReport(res, container) {
      var modal = createModal(t('importReport'));
      var body = modal.querySelector('.pa-modal-body');

      if (res.summary) {
        var s = res.summary;
        var stats = el('div', { className: 'pa-grid-3' });
        stats.appendChild(createStatMini(t('imported'), s.imported || 0, '#22c55e'));
        stats.appendChild(createStatMini(t('skipped'), s.skipped || 0, '#f59e0b'));
        stats.appendChild(createStatMini(t('errors'), s.errors || 0, '#ef4444'));
        body.appendChild(stats);
      }

      if (res.errors && res.errors.length > 0) {
        var errTitle = el('h3', { style: 'font-size:14px;margin:16px 0 8px;color:#ef4444;' }, t('errors'));
        body.appendChild(errTitle);
        res.errors.forEach(function (e) {
          var errLine = el('div', {
            style: 'font-size:12px;color:#64748b;padding:4px 0;border-bottom:1px solid #f1f5f9;'
          }, t('row') + ' ' + (e.row || '-') + ': ' + (e.error || e.message || JSON.stringify(e)));
          body.appendChild(errLine);
        });
      }

      var btnRow = el('div', { style: 'display:flex;justify-content:flex-end;margin-top:16px;' });
      btnRow.appendChild(el('button', { className: 'pa-btn pa-btn-primary', onClick: closeModal }, t('closeModal')));
      body.appendChild(btnRow);
      document.getElementById('modal-container').appendChild(modal);
    }

    function createStatMini(label, value, color) {
      return el('div', { className: 'pa-stat-card' },
        el('div', { className: 'pa-stat-label' }, label),
        el('div', { className: 'pa-stat-value', style: 'color:' + (color || '#1e293b') + ';' }, fmtNum(value))
      );
    }

    /* ---- QUOTES ---- */
    RENDERERS.quotes = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('quotes_title'));
      header.appendChild(title);
      container.appendChild(header);

      var tableWrap = el('div', { className: 'pa-card', id: 'quotes-table-wrap' });
      tableWrap.appendChild(spinner());
      container.appendChild(tableWrap);

      try {
        var res = await api('/quotes?limit=100');
        var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        tableWrap.innerHTML = '';

        if (items.length === 0) {
          tableWrap.appendChild(emptyState(t('emptyState')));
          return;
        }

        var table = el('table', { className: 'pa-table' });
        var thead = el('thead');
        var headerRow = el('tr');
        [t('quoteNumber'), t('customer'), t('amount'), t('status'), t('date'), t('details')].forEach(function (h) {
          headerRow.appendChild(el('th', {}, h));
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        var tbody = el('tbody');
        items.forEach(function (q) {
          var row = el('tr');
          row.appendChild(el('td', {}, q.quote_number || q.number || ('#' + (q.id || q._id || '').toString().slice(-6))));
          row.appendChild(el('td', {}, q.customer_name || q.customer || '-'));
          row.appendChild(el('td', {}, fmtCurrency(q.total || q.amount || 0)));
          var statusBadge = el('span', {
            className: 'pa-badge pa-badge-' + (q.status === 'approved' ? 'approved' : q.status === 'rejected' ? 'rejected' : 'pending')
          }, q.status || t('status_pending'));
          row.appendChild(el('td', {}, statusBadge));
          row.appendChild(el('td', {}, fmtDate(q.created_at || q.createdAt)));

          var detailBtn = el('button', {
            className: 'pa-btn pa-btn-ghost',
            style: 'padding:4px 8px;font-size:12px;',
            onClick: function () { openQuoteDetail(q); }
          }, t('details'));
          row.appendChild(el('td', {}, detailBtn));
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        tableWrap.appendChild(table);
      } catch (err) {
        tableWrap.appendChild(emptyState(t('networkError')));
      }
    };

    function openQuoteDetail(quote) {
      var modal = createModal(t('quoteNumber') + ' ' + (quote.quote_number || quote.number || ''));
      var body = modal.querySelector('.pa-modal-body');

      var info = el('div', { className: 'pa-grid-2', style: 'margin-bottom:16px;' });
      info.appendChild(el('div', {}, el('strong', {}, t('customer') + ': '), quote.customer_name || quote.customer || '-'));
      info.appendChild(el('div', {}, el('strong', {}, t('total') + ': '), fmtCurrency(quote.total || quote.amount || 0)));
      info.appendChild(el('div', {}, el('strong', {}, t('date') + ': '), fmtDate(quote.created_at || quote.createdAt)));
      info.appendChild(el('div', {}, el('strong', {}, t('status') + ': '), quote.status || '-'));
      body.appendChild(info);

      if (quote.items && quote.items.length > 0) {
        var itemsTitle = el('h4', { style: 'margin:0 0 8px;font-size:14px;color:#475569;' }, t('items'));
        body.appendChild(itemsTitle);
        var itemsTable = el('table', { className: 'pa-table' });
        var iHead = el('thead');
        var iRow = el('tr');
        [t('product'), t('quantity'), t('price'), t('total')].forEach(function (h) {
          iRow.appendChild(el('th', {}, h));
        });
        iHead.appendChild(iRow);
        itemsTable.appendChild(iHead);
        var iBody = el('tbody');
        quote.items.forEach(function (item) {
          var r = el('tr');
          r.appendChild(el('td', {}, item.product_name || item.name || '-'));
          r.appendChild(el('td', {}, fmtNum(item.quantity || item.qty || 0)));
          r.appendChild(el('td', {}, fmtCurrency(item.price || item.unit_price || 0)));
          r.appendChild(el('td', {}, fmtCurrency(item.total || (item.quantity || 0) * (item.price || 0))));
          iBody.appendChild(r);
        });
        itemsTable.appendChild(iBody);
        body.appendChild(itemsTable);
      }

      if (quote.notes) {
        var notesSection = el('div', { style: 'margin-top:16px;' });
        notesSection.appendChild(el('strong', {}, t('notes') + ': '));
        notesSection.appendChild(el('p', { style: 'color:#475569;margin-top:4px;white-space:pre-wrap;' }, quote.notes));
        body.appendChild(notesSection);
      }

      var btnRow = el('div', { style: 'display:flex;justify-content:flex-end;margin-top:16px;' });
      btnRow.appendChild(el('button', { className: 'pa-btn pa-btn-primary', onClick: closeModal }, t('closeModal')));
      body.appendChild(btnRow);
      document.getElementById('modal-container').appendChild(modal);
    }

    /* ---- TICKETS ---- */
    RENDERERS.tickets = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('tickets_title'));
      header.appendChild(title);
      container.appendChild(header);

      var tableWrap = el('div', { className: 'pa-card', id: 'tickets-table-wrap' });
      tableWrap.appendChild(spinner());
      container.appendChild(tableWrap);

      try {
        var res = await api('/tickets?limit=100');
        var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        tableWrap.innerHTML = '';

        if (items.length === 0) {
          tableWrap.appendChild(emptyState(t('emptyState')));
          return;
        }

        var table = el('table', { className: 'pa-table' });
        var thead = el('thead');
        var headerRow = el('tr');
        [t('id'), t('subject'), t('customer'), t('priority'), t('status'), t('date')].forEach(function (h) {
          headerRow.appendChild(el('th', {}, h));
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        var tbody = el('tbody');
        items.forEach(function (tk) {
          var row = el('tr');
          row.appendChild(el('td', {}, '#' + (tk.id || tk._id || '').toString().slice(-6)));
          row.appendChild(el('td', {}, tk.subject || tk.title || '-'));
          row.appendChild(el('td', {}, tk.customer_name || tk.customer || '-'));

          var pri = (tk.priority || 'medium').toLowerCase();
          var priBadge = el('span', {
            className: 'pa-badge pa-badge-' + pri
          }, t(pri));
          row.appendChild(el('td', {}, priBadge));

          var stBadge = el('span', {
            className: 'pa-badge pa-badge-' + (tk.status === 'open' || tk.status === 'pending' ? 'pending' : tk.status === 'closed' ? 'inactive' : 'active')
          }, tk.status || '-');
          row.appendChild(el('td', {}, stBadge));
          row.appendChild(el('td', {}, fmtDate(tk.created_at || tk.createdAt)));
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        tableWrap.appendChild(table);
      } catch (err) {
        tableWrap.appendChild(emptyState(t('networkError')));
      }
    };

    /* ---- ANALYTICS ---- */
    RENDERERS.analytics = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('analytics_title'));
      header.appendChild(title);
      container.appendChild(header);

      var statsGrid = el('div', { className: 'pa-grid-4', id: 'analytics-stats' });
      statsGrid.appendChild(spinner());
      container.appendChild(statsGrid);

      var chartsRow = el('div', { className: 'pa-grid-2', id: 'analytics-charts', style: 'margin-bottom:24px;' });
      chartsRow.appendChild(el('div', { className: 'pa-card', id: 'chart-top-products', style: 'min-height:200px;' }));
      chartsRow.appendChild(el('div', { className: 'pa-card', id: 'chart-sources', style: 'min-height:200px;' }));
      container.appendChild(chartsRow);

      var monthlyCard = el('div', { className: 'pa-card', id: 'chart-monthly', style: 'margin-bottom:24px;min-height:200px;' });
      container.appendChild(monthlyCard);

      var sparkRow = el('div', { className: 'pa-card', id: 'analytics-sparks', style: 'margin-bottom:24px;' });
      container.appendChild(sparkRow);

      var querySection = el('div', { className: 'pa-card', id: 'analytics-query-section' });
      container.appendChild(querySection);

      try {
        var res = await api('/analytics/overview');
        State.analyticsCache = res;
        renderAnalyticsStats(res);
        renderAnalyticsCharts(res);
        renderSparklines(res);
      } catch (err) {
        statsGrid.innerHTML = '';
        statsGrid.appendChild(emptyState(t('networkError')));
      }

      renderQuerySection(querySection);
    };

    function renderAnalyticsStats(data) {
      var statsGrid = $('#analytics-stats');
      if (!statsGrid) return;
      statsGrid.innerHTML = '';

      var stats = [
        { label: t('totalCustomers'), value: data.total_customers || data.customers || 0, icon: '&#128100;', color: '#3b82f6' },
        { label: t('totalQuotes'), value: data.total_quotes || data.quotes || 0, icon: '&#128196;', color: '#8b5cf6' },
        { label: t('totalTickets'), value: data.total_tickets || data.tickets || 0, icon: '&#128172;', color: '#f59e0b' },
        { label: t('totalRevenue'), value: fmtCurrency(data.total_revenue || data.revenue || 0), icon: '&#128176;', color: '#22c55e', raw: true }
      ];

      stats.forEach(function (s) {
        var card = el('div', { className: 'pa-stat-card' });
        card.appendChild(el('div', { className: 'pa-stat-icon', html: s.icon }));
        card.appendChild(el('div', { className: 'pa-stat-value', style: 'color:' + s.color + ';' },
          s.raw ? s.value : fmtNum(s.value)));
        card.appendChild(el('div', { className: 'pa-stat-label' }, s.label));
        statsGrid.appendChild(card);
      });

      if (data.avg_quote_value != null) {
        var avgCard = el('div', { className: 'pa-stat-card' });
        avgCard.appendChild(el('div', { className: 'pa-stat-icon', html: '&#128200;' }));
        avgCard.appendChild(el('div', { className: 'pa-stat-value', style: 'color:#0ea5e9;' }, fmtCurrency(data.avg_quote_value)));
        avgCard.appendChild(el('div', { className: 'pa-stat-label' }, t('avgQuote')));
        statsGrid.appendChild(avgCard);
      }
    }

    function renderAnalyticsCharts(data) {
      renderBarChart('chart-top-products', t('topProducts'), data.top_products || data.topProducts || []);
      renderPieChart('chart-sources', t('sourcesBreakdown'), data.sources || data.source_breakdown || data.customer_sources || []);
      renderBarChart('chart-monthly', t('monthlySales'), data.monthly_sales || data.monthlySales || []);
    }

    function renderBarChart(containerId, title, items) {
      var container = $('#' + containerId);
      if (!container) return;
      container.innerHTML = '';

      var titleEl = el('h3', { style: 'font-size:14px;font-weight:600;color:#1e293b;margin:0 0 16px;' }, title);
      container.appendChild(titleEl);

      if (!items || items.length === 0) {
        container.appendChild(emptyState(t('noData')));
        return;
      }

      var maxVal = Math.max.apply(null, items.map(function (i) { return i.value || i.count || 0; })) || 1;
      var bar = el('div', { className: 'pa-bar' });

      items.forEach(function (item) {
        var val = item.value || item.count || 0;
        var pct = Math.max((val / maxVal) * 100, 2);
        var col = el('div', { className: 'pa-bar-col' });
        var valLabel = el('div', { className: 'pa-bar-value' }, fmtNum(val));
        var rect = el('div', {
          className: 'pa-bar-rect',
          style: 'height:' + pct + '%;'
        });
        var label = el('div', { className: 'pa-bar-label' }, item.name || item.label || item.product || item.source || '');
        col.appendChild(valLabel);
        col.appendChild(rect);
        col.appendChild(label);
        bar.appendChild(col);
      });
      container.appendChild(bar);
    }

    function renderPieChart(containerId, title, items) {
      var container = $('#' + containerId);
      if (!container) return;
      container.innerHTML = '';

      var titleEl = el('h3', { style: 'font-size:14px;font-weight:600;color:#1e293b;margin:0 0 16px;' }, title);
      container.appendChild(titleEl);

      if (!items || items.length === 0) {
        container.appendChild(emptyState(t('noData')));
        return;
      }

      var total = items.reduce(function (sum, i) { return sum + (i.value || i.count || 0); }, 0) || 1;
      var colors = ['#3b82f6', '#8b5cf6', '#22c55e', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

      var legend = el('div', { style: 'display:flex;flex-wrap:wrap;gap:12px;margin-top:8px;' });
      items.forEach(function (item, idx) {
        var val = item.value || item.count || 0;
        var pct = ((val / total) * 100).toFixed(1);
        var color = colors[idx % colors.length];

        var legendItem = el('div', { style: 'display:flex;align-items:center;gap:6px;font-size:13px;' });
        var dot = el('span', {
          style: 'width:12px;height:12px;border-radius:3px;background:' + color + ';display:inline-block;'
        });
        legendItem.appendChild(dot);
        legendItem.appendChild(el('span', {},
          (item.name || item.label || item.source || '-') + ': ' + fmtNum(val) + ' (' + pct + '%)'));
        legend.appendChild(legendItem);
      });

      var bar = el('div', { style: 'display:flex;height:24px;border-radius:8px;overflow:hidden;margin-bottom:8px;' });
      items.forEach(function (item, idx) {
        var val = item.value || item.count || 0;
        var pct = (val / total) * 100;
        var color = colors[idx % colors.length];
        bar.appendChild(el('div', {
          style: 'width:' + pct + '%;background:' + color + ';transition:width .3s;',
          title: (item.name || item.label || item.source || '-') + ': ' + pct.toFixed(1) + '%'
        }));
      });

      container.appendChild(bar);
      container.appendChild(legend);
    }

    function renderSparklines(data) {
      var container = $('#analytics-sparks');
      if (!container) return;
      container.innerHTML = '';

      var title = el('h3', { style: 'font-size:14px;font-weight:600;color:#1e293b;margin:0 0 12px;' }, t('sparks_last7'));
      container.appendChild(title);

      var series = data.daily || data.sparklines || data.last_7_days || [];
      if (!series || series.length === 0) {
        container.appendChild(emptyState(t('noData')));
        return;
      }

      var maxVal = Math.max.apply(null, series.map(function (d) { return d.value || d.count || d.quotes || 0; })) || 1;
      var spark = el('div', { className: 'pa-sparkline', style: 'height:60px;margin-bottom:8px;' });

      series.forEach(function (d) {
        var val = d.value || d.count || d.quotes || 0;
        var pct = Math.max((val / maxVal) * 100, 4);
        var barEl = el('div', {
          className: 'pa-spark-bar',
          style: 'height:' + pct + '%;',
          title: fmtDate(d.date || d.day) + ': ' + fmtNum(val)
        });
        spark.appendChild(barEl);
      });
      container.appendChild(spark);

      var labels = el('div', { style: 'display:flex;justify-content:space-between;font-size:10px;color:#94a3b8;' });
      if (series.length > 0) {
        labels.appendChild(el('span', {}, fmtDate(series[0].date || series[0].day).split(',')[0] || ''));
        if (series.length > 1) {
          var mid = Math.floor(series.length / 2);
          labels.appendChild(el('span', {}, fmtDate(series[mid].date || series[mid].day).split(',')[0] || ''));
        }
        labels.appendChild(el('span', {}, fmtDate(series[series.length - 1].date || series[series.length - 1].day).split(',')[0] || ''));
      }
      container.appendChild(labels);
    }

    async function renderQuerySection(container) {
      container.innerHTML = '';
      var title = el('h3', { style: 'font-size:14px;font-weight:600;color:#1e293b;margin:0 0 12px;' }, t('analytics_query'));
      container.appendChild(title);

      var queryGrid = el('div', { className: 'pa-grid-2', style: 'margin-bottom:12px;' });

      var templateSelect = el('select', { className: 'pa-form-select', id: 'query-template' });
      templateSelect.appendChild(el('option', { value: '' }, t('selectTemplate')));

      var paramsInput = el('textarea', {
        className: 'pa-form-textarea',
        id: 'query-params',
        placeholder: t('enterParams'),
        style: 'min-height:60px;'
      });

      queryGrid.appendChild(el('div', {}, templateSelect));
      queryGrid.appendChild(el('div', {}, paramsInput));
      container.appendChild(queryGrid);

      try {
        var templates = await api('/analytics/templates');
        var tplList = (templates && templates.items) ? templates.items : (Array.isArray(templates) ? templates : []);
        tplList.forEach(function (tpl) {
          var key = tpl.key || tpl.name || tpl.id || '';
          var opt = el('option', { value: key }, tpl.label || tpl.description || key);
          templateSelect.appendChild(opt);
        });
      } catch (e) { /* templates optional */ }

      var btnRow = el('div', { style: 'display:flex;gap:8px;margin-bottom:12px;' });
      var runBtn = el('button', {
        className: 'pa-btn pa-btn-primary',
        onClick: async function () {
          var template = templateSelect.value;
          var params = {};
          try {
            var pVal = paramsInput.value.trim();
            if (pVal) params = JSON.parse(pVal);
          } catch (e) {
            toast('Invalid JSON', 'error');
            return;
          }
          runBtn.disabled = true;
          runBtn.textContent = t('loading');
          try {
            var result = await api('/analytics/query', {
              method: 'POST',
              body: { template: template, params: params }
            });
            renderQueryResult(result);
          } catch (err) {
            toast(err.message, 'error');
          }
          runBtn.disabled = false;
          runBtn.textContent = t('runQuery');
        }
      }, t('runQuery'));
      btnRow.appendChild(runBtn);
      container.appendChild(btnRow);

      var resultDiv = el('div', { id: 'query-result' });
      container.appendChild(resultDiv);
    }

    function renderQueryResult(result) {
      var resultDiv = $('#query-result');
      if (!resultDiv) return;
      resultDiv.innerHTML = '';

      if (!result) {
        resultDiv.appendChild(emptyState(t('noResults')));
        return;
      }

      var resultCard = el('div', { className: 'pa-card', style: 'margin-top:0;' });
      var resultTitle = el('h4', { style: 'font-size:13px;color:#475569;margin:0 0 8px;' }, t('queryResult'));
      resultCard.appendChild(resultTitle);

      if (Array.isArray(result) || (result && result.rows)) {
        var rows = Array.isArray(result) ? result : (result.rows || []);
        if (rows.length === 0) {
          resultCard.appendChild(emptyState(t('noResults')));
        } else {
          var table = el('table', { className: 'pa-table' });
          var keys = Object.keys(rows[0]);
          var thead = el('thead');
          var hRow = el('tr');
          keys.forEach(function (k) { hRow.appendChild(el('th', {}, k)); });
          thead.appendChild(hRow);
          table.appendChild(thead);
          var tbody = el('tbody');
          rows.forEach(function (row) {
            var r = el('tr');
            keys.forEach(function (k) { r.appendChild(el('td', {}, String(row[k] != null ? row[k] : ''))); });
            tbody.appendChild(r);
          });
          table.appendChild(tbody);
          resultCard.appendChild(table);
        }
      } else {
        var pre = el('pre', {
          style: 'font-size:12px;background:#f8fafc;padding:12px;border-radius:8px;overflow-x:auto;white-space:pre-wrap;'
        }, JSON.stringify(result, null, 2));
        resultCard.appendChild(pre);
      }

      resultDiv.appendChild(resultCard);
    }

    /* ---- AUDIT ---- */
    RENDERERS.audit = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('audit_title'));
      header.appendChild(title);
      container.appendChild(header);

      var tableWrap = el('div', { className: 'pa-card', id: 'audit-table-wrap' });
      tableWrap.appendChild(spinner());
      container.appendChild(tableWrap);

      try {
        var res = await api('/audit?limit=200');
        var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        tableWrap.innerHTML = '';

        if (items.length === 0) {
          tableWrap.appendChild(emptyState(t('emptyState')));
          return;
        }

        var table = el('table', { className: 'pa-table' });
        var thead = el('thead');
        var headerRow = el('tr');
        [t('date'), t('id'), 'Action', 'Actor', 'Details'].forEach(function (h) {
          headerRow.appendChild(el('th', {}, h));
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);
        var tbody = el('tbody');
        items.forEach(function (a) {
          var row = el('tr');
          row.appendChild(el('td', { style: 'white-space:nowrap;' }, fmtDate(a.timestamp || a.created_at || a.createdAt)));
          row.appendChild(el('td', {}, '#' + (a.id || a._id || '').toString().slice(-6)));
          row.appendChild(el('td', {}, el('span', {
            className: 'pa-badge pa-badge-' + (a.action === 'approve' || a.action === 'create' ? 'approved' : a.action === 'reject' || a.action === 'delete' ? 'rejected' : 'pending')
          }, a.action || a.event || '-')));
          row.appendChild(el('td', {}, a.actor || a.admin || a.user || '-'));
          var detailsText = '';
          if (a.details) {
            detailsText = typeof a.details === 'string' ? a.details : JSON.stringify(a.details);
          } else if (a.note) {
            detailsText = a.note;
          } else if (a.description) {
            detailsText = a.description;
          }
          row.appendChild(el('td', {
            style: 'max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:#64748b;',
            title: detailsText
          }, detailsText || '-'));
          tbody.appendChild(row);
        });
        table.appendChild(tbody);
        tableWrap.appendChild(table);
      } catch (err) {
        tableWrap.appendChild(emptyState(t('networkError')));
      }
    };

    /* ---- TEMPLATES ---- */
    RENDERERS.templates = async function (container) {
      container.innerHTML = '';
      var header = el('div', { className: 'pa-toolbar' });
      var title = el('h2', { className: 'pa-section-title', style: 'margin:0;flex:1;' }, t('templates_title'));
      header.appendChild(title);
      container.appendChild(header);

      var content = el('div', { id: 'templates-content' });
      content.appendChild(spinner());
      container.appendChild(content);

      try {
        var res = await api('/templates');
        var items = (res && res.items) ? res.items : (Array.isArray(res) ? res : []);
        State.templatesCache = items;
        renderTemplateList(items, content);
      } catch (err) {
        content.innerHTML = '';
        content.appendChild(emptyState(t('networkError')));
      }
    };

    function renderTemplateList(items, container) {
      container.innerHTML = '';

      if (!items || items.length === 0) {
        container.appendChild(emptyState(t('noTemplates')));
        return;
      }

      items.forEach(function (tpl) {
        var card = el('div', { className: 'pa-card' });
        var cardHeader = el('div', { style: 'display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;' });
        var tplKey = el('span', { style: 'font-weight:600;color:#1e293b;font-size:14px;' }, tpl.key || tpl.name || '-');
        var tplLang = el('span', {
          className: 'pa-badge pa-badge-pending',
          style: 'margin-inline-start:8px;'
        }, (tpl.lang || tpl.language || State.lang).toUpperCase());
        var tplActive = el('span', {
          className: 'pa-badge ' + (tpl.active !== false ? 'pa-badge-active' : 'pa-badge-inactive'),
          style: 'margin-inline-start:8px;'
        }, tpl.active !== false ? t('status_active') : t('status_inactive'));

        cardHeader.appendChild(tplKey);
        cardHeader.appendChild(tplLang);
        cardHeader.appendChild(tplActive);

        var bodyPreview = el('div', {
          style: 'font-size:13px;color:#475569;line-height:1.6;white-space:pre-wrap;max-height:80px;overflow:hidden;margin-bottom:12px;background:#f8fafc;padding:12px;border-radius:8px;',
          html: escHtml(truncate(tpl.body || tpl.content || tpl.text || '', 300))
        });

        var btnRow = el('div', { style: 'display:flex;gap:8px;flex-wrap:wrap;' });
        var editBtn = el('button', {
          className: 'pa-btn pa-btn-primary',
          onClick: function () { openTemplateEditor(tpl, container); }
        }, t('edit'));
        var resetBtn = el('button', {
          className: 'pa-btn pa-btn-warning',
          onClick: function () { resetTemplate(tpl, container); }
        }, t('reset'));
        btnRow.appendChild(editBtn);
        btnRow.appendChild(resetBtn);

        card.appendChild(cardHeader);
        card.appendChild(bodyPreview);
        card.appendChild(btnRow);
        container.appendChild(card);
      });
    }

    function truncate(str, max) {
      if (!str) return '';
      return str.length > max ? str.substring(0, max) + '...' : str;
    }

    function openTemplateEditor(tpl, container) {
      var modal = createModal(t('edit') + ': ' + (tpl.key || tpl.name || ''));
      var body = modal.querySelector('.pa-modal-body');

      var form = el('form');
      form.addEventListener('submit', async function (e) {
        e.preventDefault();
        var data = {
          key: tpl.key || tpl.name,
          lang: tpl.lang || tpl.language || State.lang,
          body: bodyArea.value,
          active: tpl.active
        };
        try {
          await api('/templates', { method: 'PUT', body: data });
          toast(t('templateSaved'), 'success');
          closeModal();
          if (container) navigate(State.view);
        } catch (err) {
          toast(err.message, 'error');
        }
      });

      var keyGroup = el('div', { className: 'pa-form-group' });
      keyGroup.appendChild(el('label', { className: 'pa-form-label' }, t('templateKey')));
      keyGroup.appendChild(el('input', {
        className: 'pa-form-input',
        value: tpl.key || tpl.name || '',
        disabled: 'disabled'
      }));
      form.appendChild(keyGroup);

      var langGroup = el('div', { className: 'pa-form-group' });
      langGroup.appendChild(el('label', { className: 'pa-form-label' }, t('templateLang')));
      langGroup.appendChild(el('input', {
        className: 'pa-form-input',
        value: (tpl.lang || tpl.language || State.lang).toUpperCase(),
        disabled: 'disabled'
      }));
      form.appendChild(langGroup);

      var bodyGroup = el('div', { className: 'pa-form-group' });
      bodyGroup.appendChild(el('label', { className: 'pa-form-label' }, t('templateBody')));
      var bodyArea = el('textarea', {
        className: 'pa-form-textarea',
        style: 'min-height:200px;font-family:monospace;font-size:13px;'
      });
      bodyArea.value = tpl.body || tpl.content || tpl.text || '';
      bodyGroup.appendChild(bodyArea);
      form.appendChild(bodyGroup);

      var btnRow = el('div', { style: 'display:flex;gap:8px;justify-content:flex-end;margin-top:16px;' });
      btnRow.appendChild(el('button', { className: 'pa-btn pa-btn-ghost', type: 'button', onClick: closeModal }, t('cancel')));
      btnRow.appendChild(el('button', { className: 'pa-btn pa-btn-primary', type: 'submit' }, t('save')));
      form.appendChild(btnRow);

      body.appendChild(form);
      document.getElementById('modal-container').appendChild(modal);
    }

    async function resetTemplate(tpl, container) {
      try {
        await api('/templates/reset?key=' + encodeURIComponent(tpl.key || tpl.name) + '&lang=' + encodeURIComponent(tpl.lang || tpl.language || State.lang), {
          method: 'POST'
        });
        toast(t('templateReset'), 'success');
        if (container) navigate(State.view);
      } catch (err) {
        toast(err.message, 'error');
      }
    }

    /* ---- ROUTER ---- */
    RENDERERS.router = async function (container) {
      container.innerHTML = '';

      var card = el('div', { className: 'pa-card', style: 'text-align:center;padding:60px 24px;' });
      var icon = el('div', { style: 'font-size:48px;margin-bottom:16px;' }, '&#128279;');
      var title = el('h2', { style: 'font-size:20px;font-weight:700;color:#1e293b;margin:0 0 8px;' }, t('router_title'));
      var desc = el('p', { style: 'font-size:14px;color:#64748b;margin:0 0 24px;max-width:500px;margin-inline:auto;' }, t('router_desc'));
      var linkBtn = el('a', {
        href: '/admin/9router/',
        className: 'pa-btn pa-btn-primary',
        style: 'text-decoration:none;font-size:15px;padding:12px 32px;',
        target: '_blank'
      }, t('openRouter'));
      card.appendChild(icon);
      card.appendChild(title);
      card.appendChild(desc);
      card.appendChild(linkBtn);
      container.appendChild(card);

      var infoCard = el('div', { className: 'pa-card', style: 'margin-top:16px;' });
      var infoTitle = el('h3', { style: 'font-size:16px;font-weight:600;color:#1e293b;margin:0 0 12px;' }, t('overview'));
      infoCard.appendChild(infoTitle);

      var infoList = el('div', { style: 'display:grid;grid-template-columns:1fr 1fr;gap:12px;' });
      var features = [
        { icon: '&#128203;', label: State.lang === 'ar' ? 'قواعد التوجيه' : 'Routing Rules' },
        { icon: '&#128100;', label: State.lang === 'ar' ? 'تعيين العملاء' : 'Customer Assignment' },
        { icon: '&#128176;', label: State.lang === 'ar' ? 'تتبع المبيعات' : 'Sales Tracking' },
        { icon: '&#128202;', label: State.lang === 'ar' ? 'تقارير الأداء' : 'Performance Reports' }
      ];
      features.forEach(function (f) {
        var item = el('div', {
          style: 'display:flex;align-items:center;gap:10px;padding:12px;background:#f8fafc;border-radius:8px;'
        });
        item.appendChild(el('span', { style: 'font-size:20px;' }, f.icon));
        item.appendChild(el('span', { style: 'font-size:13px;color:#475569;' }, f.label));
        infoList.appendChild(item);
      });
      infoCard.appendChild(infoList);
      container.appendChild(infoCard);
    };

  /* ---------------------------------------------------------
     10. MODALS
     --------------------------------------------------------- */
  function createModal(titleText) {
    var overlay = el('div', {
      className: 'pa-modal-overlay',
      onClick: function (e) {
        if (e.target === overlay) closeModal();
      }
    });
    var modal = el('div', { className: 'pa-modal' });
    var header = el('div', { className: 'pa-modal-header' });
    var titleEl = el('div', { className: 'pa-modal-title' }, titleText);
    var closeBtn = el('button', {
      className: 'pa-modal-close',
      onClick: closeModal,
      html: '&times;',
      'aria-label': t('closeModal')
    });
    header.appendChild(titleEl);
    header.appendChild(closeBtn);
    var body = el('div', { className: 'pa-modal-body' });
    modal.appendChild(header);
    modal.appendChild(body);
    overlay.appendChild(modal);

    var escHandler = function (e) {
      if (e.key === 'Escape') {
        closeModal();
        document.removeEventListener('keydown', escHandler);
      }
    };
    document.addEventListener('keydown', escHandler);
    State.modalStack.push(escHandler);

    return overlay;
  }

  function openModal(content) {
    var container = $('#modal-container');
    if (!container) return;
    container.innerHTML = '';
    var overlay = el('div', { className: 'pa-modal-overlay', onClick: function (e) { if (e.target === overlay) closeModal(); } });
    var modal = el('div', { className: 'pa-modal' });
    if (typeof content === 'string') {
      modal.innerHTML = content;
    } else if (content instanceof Node) {
      modal.appendChild(content);
    }
    overlay.appendChild(modal);
    container.appendChild(overlay);
  }

  function closeModal() {
    var container = $('#modal-container');
    if (container) container.innerHTML = '';
    if (State.modalStack.length > 0) {
      var handler = State.modalStack.pop();
      if (handler) document.removeEventListener('keydown', handler);
    }
  }

  /* ---------------------------------------------------------
     11. APPROVAL ACTIONS
     --------------------------------------------------------- */
    async function decide(id, decision) {
      if (!id) return;
      var msg = decision === 'approved' ? t('confirmApprove') : t('confirmReject');
      if (!confirm(msg)) return;

      try {
        await api('/approvals/' + id + '/decision', {
          method: 'POST',
          body: { decision: decision }
        });
        toast(decision === 'approved' ? t('approve') : t('reject'), 'success');
        navigate(State.view);
      } catch (err) {
        toast(err.message, 'error');
      }
    }

    function openEdit(item) {
      State.editingApproval = item;
      var modal = createModal(t('editApprovalTitle'));
      var body = modal.querySelector('.pa-modal-body');

      var origGroup = el('div', { className: 'pa-form-group' });
      origGroup.appendChild(el('label', { className: 'pa-form-label' }, t('originalText')));
      origGroup.appendChild(el('div', {
        style: 'padding:10px;background:#f8fafc;border-radius:8px;font-size:13px;color:#475569;white-space:pre-wrap;max-height:100px;overflow-y:auto;'
      }, item.text || item.body || item.content || item.original_text || ''));
      body.appendChild(origGroup);

      var editGroup = el('div', { className: 'pa-form-group' });
      editGroup.appendChild(el('label', { className: 'pa-form-label' }, t('editedText')));
      var editArea = el('textarea', {
        className: 'pa-form-textarea',
        style: 'min-height:100px;'
      });
      editArea.value = item.text || item.body || item.content || item.original_text || '';
      editGroup.appendChild(editArea);
      body.appendChild(editGroup);

      var noteGroup = el('div', { className: 'pa-form-group' });
      noteGroup.appendChild(el('label', { className: 'pa-form-label' }, t('approvalNote')));
      var noteArea = el('textarea', {
        className: 'pa-form-textarea',
        style: 'min-height:60px;'
      });
      noteArea.value = item.note || item.admin_note || '';
      noteGroup.appendChild(noteArea);
      body.appendChild(noteGroup);

      var btnRow = el('div', { style: 'display:flex;gap:8px;justify-content:flex-end;margin-top:16px;' });
      btnRow.appendChild(el('button', { className: 'pa-btn pa-btn-ghost', onClick: closeModal }, t('cancel')));

      var approveBtn = el('button', {
        className: 'pa-btn pa-btn-success',
        onClick: async function () {
          try {
            await api('/approvals/' + (item.id || item._id) + '/decision', {
              method: 'POST',
              body: {
                decision: 'approved',
                edited_text: editArea.value,
                note: noteArea.value
              }
            });
            toast(t('approve'), 'success');
            closeModal();
            navigate(State.view);
          } catch (err) {
            toast(err.message, 'error');
          }
        }
      }, t('approve'));

      var rejectBtn = el('button', {
        className: 'pa-btn pa-btn-danger',
        onClick: async function () {
          try {
            await api('/approvals/' + (item.id || item._id) + '/decision', {
              method: 'POST',
              body: {
                decision: 'rejected',
                edited_text: editArea.value,
                note: noteArea.value
              }
            });
            toast(t('reject'), 'success');
            closeModal();
            navigate(State.view);
          } catch (err) {
            toast(err.message, 'error');
          }
        }
      }, t('reject'));

      btnRow.appendChild(rejectBtn);
      btnRow.appendChild(approveBtn);
      body.appendChild(btnRow);
      document.getElementById('modal-container').appendChild(modal);
    }

    function openApproval(item) {
      if (item && item.status === 'pending') {
        openEdit(item);
      }
    }

  /* ---------------------------------------------------------
     12. HASH ROUTING
     --------------------------------------------------------- */
  window.addEventListener('hashchange', function () {
    var hash = window.location.hash.replace('#', '').replace('/', '');
    if (hash && VIEWS.indexOf(hash) !== -1 && hash !== State.view) {
      State.view = hash;
      navigate(hash);
    }
  });

  /* ---------------------------------------------------------
     13. CSS keyframes injection (non-dynamic)
     --------------------------------------------------------- */
  function injectBaseCSS() {
    if ($('#pa-base-css')) return;
    var style = document.createElement('style');
    style.id = 'pa-base-css';
    style.textContent = '\n' +
      '* { margin:0; padding:0; box-sizing:border-box; }\n' +
      'body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif, "Noto Sans Arabic"; background:#f1f5f9; color:#334155; line-height:1.5; }\n' +
      'button { cursor:pointer; }\n' +
      'input:focus, textarea:focus, select:focus { outline:none; }\n' +
      '[dir=rtl] { text-align:right; }\n' +
      '[dir=ltr] { text-align:left; }\n' +
      '.pa-login-card input:focus { border-color:#3b82f6 !important; box-shadow:0 0 0 3px rgba(59,130,246,.1); }\n' +
      '.pa-btn:active { transform:scale(.97); }\n' +
      '.pa-card { animation:paFadeIn .2s ease; }\n' +
      '.pa-toast { animation:paSlideIn .3s ease; }\n' +
      '.pa-table-wrap { overflow-x:auto; }\n' +
      'a { color:#3b82f6; }\n' +
      'a:hover { color:#2563eb; }\n' +
      '\n';
    document.head.appendChild(style);
  }

  /* ---------------------------------------------------------
     14. BOOTSTRAP
     --------------------------------------------------------- */
  function boot() {
    injectBaseCSS();
    checkSession();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  /* ---------------------------------------------------------
     Expose minimal API for debugging
     --------------------------------------------------------- */
  window.KiaAgentAdmin = {
    navigate: navigate,
    setLang: function (lang) {
      if (lang === 'ar' || lang === 'en') {
        State.lang = lang;
        localStorage.setItem('pa_lang', lang);
        applyI18n();
        navigate(State.view);
      }
    },
    getState: function () { return Object.assign({}, State, { eventSource: null }); },
    refreshQueue: refreshQueue
  };

})();
