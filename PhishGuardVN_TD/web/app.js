'use strict';
const app = document.querySelector('#app');
let me = null;
let page = 'check';
let toastTimer;
const $ = (tag, attrs = {}, ...children) => { const el = document.createElement(tag); for (const [k, v] of Object.entries(attrs)) { if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v);
        else if (k === 'class') el.className = v;
        else el.setAttribute(k, v); } for (const c of children.flat()) { if (c !== null && c !== undefined) el.append(c instanceof Node ? c : document.createTextNode(String(c))); } return el; };

function notice(message, error = false) { const t = document.querySelector('#toast');
    t.textContent = message;
    t.className = 'show' + (error ? ' error' : '');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.className = '', 6500); }
async function api(path, method = 'GET', body) { const res = await fetch('/api' + path, { method, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', ...(me ? { 'X-CSRF-Token': me.csrf } : {}) }, body: body === undefined ? undefined : JSON.stringify(body) }); let result; try { result = await res.json(); } catch { throw Error('Không nhận được phản hồi hợp lệ từ máy chủ.'); } if (!res.ok) { const message = typeof result.detail === 'string' ? result.detail : 'Dữ liệu chưa hợp lệ. Kiểm tra lại các trường.'; if (res.status === 401 && me) { me = null;
            auth(); } throw Error(message); } return result; }

function safe(fn) { return async e => { try { await fn(e); } catch (err) { notice(err.message, true); } }; }

function button(label, fn, cls = '') { return $('button', { type: 'button', class: cls, onclick: safe(fn) }, label); }

function field(label, input) { return [$('label', { for: input.id }, label), input]; }

function card(title, ...content) { return $('section', { class: 'card' }, title ? $('h3', {}, title) : null, ...content); }

function table(headers, rows) { return $('div', { class: 'table-wrap' }, $('table', {}, $('thead', {}, $('tr', {}, headers.map(x => $('th', {}, x)))), $('tbody', {}, rows.map(row => $('tr', {}, row.map(cell => $('td', {}, cell))))))); }

function badge(status) { return $('span', { class: 'badge ' + status }, ({ pending: 'Chờ duyệt', approved: 'Đã duyệt', rejected: 'Từ chối' })[status] || status); }

function date(s) { return s ? new Date(s).toLocaleString('vi-VN') : '—'; }

function auth(register = false) {
    app.replaceChildren();
    const user = $('input', { id: 'username', required: '', autocomplete: 'username', placeholder: 'Tên đăng nhập', pattern: '(?:[a-zA-Z0-9_.]|-){3,40}' });
    const pass = $('input', { id: 'password', type: 'password', required: '', minlength: 10, maxlength: 128, autocomplete: register ? 'new-password' : 'current-password', placeholder: 'Ít nhất 10 ký tự' });
    const submit = $('button', { type: 'submit' }, register ? 'Tạo tài khoản' : 'Đăng nhập');
    const form = $('form', { onsubmit: safe(async e => { e.preventDefault();
            submit.disabled = true; try { const body = { username: user.value, password: pass.value }; if (register) { await api('/auth/register', 'POST', body);
                    notice('Đã tạo tài khoản. Hãy đăng nhập.');
                    auth(false); } else { me = await api('/auth/login', 'POST', body);
                    page = 'check';
                    shell(); } } finally { submit.disabled = false; } }) }, field('Tên đăng nhập', user), field('Mật khẩu', pass), submit);
    app.append($('div', { class: 'auth-shell' }, $('section', { class: 'auth-story' }, $('div', { class: 'brand' }, '◈ PhishGuard', $('em', {}, 'VN')), $('p', { class: 'eyebrow' }, 'KIỂM TRA · NHẬN BIẾT · BÁO CÁO'), $('h1', {}, 'Chậm một nhịp.', ' ', $('br'), 'An tâm hơn một bước.'), $('p', {}, 'Kiểm tra tin nhắn và liên kết đáng ngờ, theo dõi dấu hiệu thao túng và tham khảo báo cáo đã được kiểm duyệt từ cộng đồng.'), $('p', { class: 'notice-line' }, 'Đồ án tốt nghiệp · Phiên bản nghiên cứu 0.5')), $('section', { class: 'auth-form' }, $('div', {}, $('div', { class: 'eyebrow' }, 'CHÀO MỪNG BẠN'), $('h2', {}, register ? 'Tạo tài khoản mới' : 'Đăng nhập PhishGuardVN'), $('p', { class: 'muted' }, 'Lịch sử kiểm tra và báo cáo được lưu trong tài khoản của bạn.'), form, button(register ? 'Đã có tài khoản? Đăng nhập' : 'Chưa có tài khoản? Đăng ký', () => auth(!register), 'secondary'), $('div', { class: 'auth-foot' }, 'Kết quả AI là tín hiệu tham khảo. Không gửi mật khẩu, mã OTP thật hoặc thông tin bí mật vào hệ thống.')))));
}

function shell() { app.replaceChildren(); const nav = $('nav'); const navItems = [
        ['check', '◎  Kiểm tra nội dung'],
        ['lookup', '⌕  Tra cứu cộng đồng'],
        ['reports', '▤  Báo cáo của tôi'],
        ['history', '↺  Lịch sử kiểm tra'],
        ['stats', '▥  Thống kê của tôi'],
        ['account', '⚙  Tài khoản']
    ]; if (me.role === 'admin') navItems.push(['admin_reports', '▣  Duyệt báo cáo'], ['admin_users', '♙  Quản lý người dùng'], ['admin_stats', '▥  Thống kê hệ thống'], ['audit', '≡  Nhật ký quản trị']); for (const [key, label] of navItems) nav.append(button(label, () => { page = key;
        shell(); }, page === key ? 'active' : '')); const main = $('main', { class: 'content' }, $('header', { class: 'topbar' }, $('span', {}, 'Không gian ' + (page.startsWith('admin') ? 'quản trị' : 'của bạn')), $('span', { class: 'pill' }, me.role === 'admin' ? 'Quản trị viên' : 'Thành viên'))); const view = $('div', { id: 'view' });
    main.append(view, $('footer', {}, 'PhishGuardVN · AI hỗ trợ nhận diện rủi ro · Báo cáo cộng đồng qua kiểm duyệt'));
    app.append($('div', { class: 'layout' }, $('aside', { class: 'sidebar' }, $('div', { class: 'brand' }, '◈ PhishGuard', $('em', {}, 'VN')), $('div', { class: 'nav-label' }, 'KHÔNG GIAN LÀM VIỆC'), nav, $('div', { class: 'account' }, me.username, button('Đăng xuất', async() => { await api('/auth/logout', 'POST', {});
        me = null;
        auth(); }))), main));
    render(view).catch(e => notice(e.message, true)); }

function heading(view, title, desc) { view.append($('div', { class: 'eyebrow' }, 'PHISHGUARDVN'), $('h1', { class: 'page-title' }, title), $('p', { class: 'subtitle' }, desc)); }
async function render(view) { if (page === 'check') checkView(view);
    else if (page === 'lookup') lookupView(view);
    else if (page === 'reports') await reportsView(view, false);
    else if (page === 'admin_reports') await reportsView(view, true);
    else if (page === 'history') await historyView(view);
    else if (page === 'stats' || page === 'admin_stats') await statsView(view);
    else if (page === 'admin_users') await usersView(view);
    else if (page === 'account') accountView(view);
    else if (page === 'audit') { heading(view, 'Nhật ký quản trị', 'Theo dõi thao tác gần đây để kiểm tra trách nhiệm xử lý.'); const r = await api('/admin/audit');
        view.append(card('', table(['Thời gian', 'Người dùng', 'Thao tác', 'Đối tượng', 'Chi tiết'], r.items.map(x => [date(x.created_at), x.user_id, x.action, x.object_id, x.detail])))); } }

function checkView(view) { heading(view, 'Kiểm tra trước khi tin tưởng', 'Dán nội dung tin nhắn hoặc liên kết. Hệ thống phân tích từng URL và những dấu hiệu đáng chú ý trong lời nhắn.'); const text = $('textarea', { id: 'check-text', maxlength: 6000, placeholder: 'Dán tin nhắn cần kiểm tra…', rows: 7 }); const urls = $('textarea', { id: 'check-urls', placeholder: 'https://example.com\nMỗi URL một dòng (tối đa 20)', rows: 2 }); const result = $('div', { id: 'result' }, card('Kết quả kiểm tra', $('div', { class: 'empty' }, 'Kết quả sẽ hiển thị ở đây sau khi phân tích.'))); const go = $('button', { type: 'submit' }, 'Phân tích nội dung  →'); const form = $('form', { onsubmit: safe(async e => { e.preventDefault();
            go.disabled = true;
            go.textContent = 'Đang phân tích…'; try { const r = await api('/checks', 'POST', { text: text.value, urls: urls.value.split('\n').map(x => x.trim()).filter(Boolean) });
                renderResult(result, r); } finally { go.disabled = false;
                go.textContent = 'Phân tích nội dung  →'; } }) }, field('Nội dung tin nhắn', text), field('URL bổ sung (không bắt buộc)', urls), $('div', { class: 'actions' }, go, button('Xóa nội dung', () => { text.value = '';
        urls.value = ''; }, 'secondary')));
    view.append($('div', { class: 'grid' }, $('div', {}, card('Bạn muốn kiểm tra điều gì?', form), card('Cách đọc kết quả', $('p', {}, 'Điểm cảnh báo càng cao, càng nên xác minh lại người gửi và nguồn liên kết.'), $('p', { class: 'muted' }, 'Tin có nhiều URL: xem từng kết quả bên dưới. Số báo cáo của cộng đồng được tra cứu riêng; chưa có báo cáo không đồng nghĩa an toàn.'))), result)); }

function renderResult(node, r) {
    node.replaceChildren();
    node.append(card('Điểm cảnh báo tham khảo', $('div', { class: 'row between' }, $('div', { class: 'score' + (r.alert ? ' high' : '') }, r.risk_percent, $('small', {}, ' / 100')), $('span', { class: 'badge ' + (r.alert ? 'rejected' : 'approved') }, r.risk_level)), $('p', { class: 'muted' }, `Ngưỡng cảnh báo: ${(r.threshold*100).toFixed(0)} / 100 · ${r.mode==='url_only'?'Phân tích URL':r.mode==='text_only_proxy'?'Phân tích văn bản':'Văn bản + URL'}`), $('div', { class: 'note' }, r.mode === 'url_only' ? 'Kết quả mô hình URL; không đảm bảo liên kết an toàn tuyệt đối.' : 'Nhánh văn bản đang dùng nhãn spam/scam gộp chung. Điểm này chưa phải xác suất phishing đã được xác nhận.')));
    const signals = r.signals.filter(x => x.predicted || x.evidence.length);
    if (signals.length) node.append(card('Dấu hiệu trong tin nhắn', signals.map(x => $('div', { class: 'signal' }, $('strong', {}, x.name), $('p', { class: 'muted' }, x.validation_status === 'insufficient_positive_samples' ? 'Chưa đủ mẫu để dùng quyết định phân loại; hiển thị dấu hiệu câu chữ.' : `Điểm nhận diện ${(100*x.probability).toFixed(0)}% · nhãn học tự động`), x.evidence.length ? $('p', {}, x.evidence.map(m => $('mark', {}, m.text + ' '))) : $('p', { class: 'muted' }, 'Mô hình nhận diện, chưa có cụm từ khớp quy tắc.')))));
    for (const u of r.urls) node.append(card('Kết quả URL', $('p', { class: 'target' }, u.url), $('div', { class: 'row between' }, badge(u.prediction === 'Phishing' ? 'rejected' : 'approved'), $('strong', {}, `${(u.p_phishing*100).toFixed(1)}% điểm phishing`)), $('p', { class: 'muted' }, u.prediction === 'Phishing' ? 'Mô hình xếp vào lớp Phishing.' : 'Mô hình xếp vào lớp Legitimate; vẫn cần xác minh nguồn gửi.'), $('details', {}, $('summary', {}, 'Vì sao có kết quả này? · SHAP'), $('p', { class: 'muted' }, 'Giá trị dương làm tăng điểm phishing; âm làm giảm. Đóng góp ở thang log-odds, không phải phần trăm.'), table(['Đặc trưng', 'Giá trị', 'Đóng góp'], u.shap.top_features.map(x => [x.feature, x.value.toFixed(3), $('span', { class: x.contribution > 0 ? 'positive' : 'negative' }, (x.contribution > 0 ? '+' : '') + x.contribution.toFixed(3))]))), button('Báo cáo URL này', () => { page = 'reports';
        shell();
        setTimeout(() => { const t = document.querySelector('#report-target'); if (t) t.value = u.url; }, 300); }, 'secondary')));
}

function lookupView(view) { heading(view, 'Tra cứu phản ánh cộng đồng', 'Kiểm tra số điện thoại hoặc URL đã được người dùng khác báo cáo và quản trị viên duyệt.'); const type = $('select', { id: 'lookup-type' }, $('option', { value: 'phone' }, 'Số điện thoại'), $('option', { value: 'url' }, 'URL')); const input = $('input', { id: 'lookup-q', required: '', placeholder: 'Nhập số điện thoại hoặc URL cần tra cứu' }); const result = $('div'); const form = $('form', { onsubmit: safe(async e => { e.preventDefault(); const r = await api('/lookup?target_type=' + type.value + '&q=' + encodeURIComponent(input.value));
            result.replaceChildren(card('Kết quả tra cứu', $('p', { class: 'target' }, r.target), $('div', { class: 'score' + (r.approved_reports ? ' high' : '') }, r.approved_reports), $('p', {}, 'báo cáo đã được duyệt từ ' + r.unique_reporters + ' người dùng khác nhau'), $('p', { class: 'muted' }, 'Cập nhật gần nhất: ' + date(r.last_approved_update)), $('div', { class: 'note' }, r.notice))); }) }, field('Loại thông tin', type), field('Thông tin tra cứu', input), $('div', { class: 'actions' }, $('button', { type: 'submit' }, 'Tra cứu ngay')));
    view.append($('div', { class: 'grid' }, card('Tìm thông tin', form), result)); }
async function reportsView(view, isAdmin) {
    heading(view, isAdmin ? 'Duyệt báo cáo cộng đồng' : 'Báo cáo của tôi', isAdmin ? 'Xem nội dung, ghi nhận quyết định và quản lý thông tin công khai.' : 'Gửi phản ánh và theo dõi tiến độ. Mỗi người chỉ có một báo cáo đang hoạt động cho cùng đối tượng.');
    const list = $('div');
    let offset = 0;
    let status = 'all';
    let editing = null;
    let formCard;
    const type = $('select', { id: 'report-type' }, $('option', { value: 'url' }, 'URL'), $('option', { value: 'phone' }, 'Số điện thoại'));
    const target = $('input', { id: 'report-target', required: '', maxlength: 4096, placeholder: 'Thông tin cần báo cáo' });
    const description = $('textarea', { id: 'report-description', required: '', minlength: 10, maxlength: 3000, placeholder: 'Mô tả sự việc và lý do nghi ngờ. Không đưa mật khẩu, OTP hoặc thông tin riêng tư của người khác.' });
    const submit = $('button', { type: 'submit' }, 'Gửi báo cáo');
    const reset = () => { editing = null;
        type.value = 'url';
        target.value = '';
        description.value = '';
        submit.textContent = 'Gửi báo cáo'; };
    if (!isAdmin) { formCard = card('Gửi phản ánh', $('form', { onsubmit: safe(async e => { e.preventDefault(); const body = { target_type: type.value, target: target.value, description: description.value }; if (editing) { await api('/reports/' + editing.id, 'PUT', {...body, version: editing.version }); } else await api('/reports', 'POST', body);
                notice('Đã lưu báo cáo và chuyển sang chờ duyệt.');
                reset();
                await load(); }) }, field('Loại đối tượng', type), field('Số điện thoại hoặc URL', target), field('Nội dung báo cáo', description), $('div', { class: 'actions' }, submit, button('Hủy sửa', reset, 'secondary'))));
        view.append(formCard); } else { const filter = $('select', { class: 'filter', 'aria-label': 'Lọc trạng thái', onchange: safe(async e => { status = e.target.value;
                offset = 0;
                await load(); }) }, ['all', 'pending', 'approved', 'rejected'].map(x => $('option', { value: x }, ({ all: 'Tất cả', pending: 'Chờ duyệt', approved: 'Đã duyệt', rejected: 'Từ chối' })[x])));
        view.append(filter); }
    view.append(list);
    async function load() { const response = await api((isAdmin ? '/admin/reports?status=' + status + '&' : '/reports?') + 'offset=' + offset + '&limit=20');
        list.replaceChildren(card('Danh sách báo cáo', response.items.length ? table(isAdmin ? ['Đối tượng / người gửi', 'Nội dung', 'Trạng thái', 'Thao tác'] : ['Đối tượng', 'Nội dung', 'Trạng thái', 'Thao tác'], response.items.map(r => { const actions = $('div'); if (isAdmin) { for (const [s, label] of[['approved', 'Duyệt'], ['rejected', 'Từ chối']]) actions.append(button(label, async() => { const note = prompt('Nhận xét xử lý (ít nhất 3 ký tự):'); if (!note) return;
                    await api('/admin/reports/' + r.id + '/moderate', 'POST', { status: s, note, version: r.version });
                    notice('Đã cập nhật trạng thái.');
                    await load(); }, s === 'approved' ? '' : 'secondary'));
                actions.append(button('Xóa', async() => { if (!confirm('Xóa báo cáo này khỏi danh sách và tra cứu cộng đồng?')) return;
                    await api('/admin/reports/' + r.id, 'DELETE');
                    await load(); }, 'danger')); } else { actions.append(button('Sửa', () => { editing = r;
                    type.value = r.target_type;
                    target.value = r.target;
                    description.value = r.description;
                    submit.textContent = 'Lưu sửa · gửi duyệt lại';
                    formCard.scrollIntoView({ behavior: 'smooth' }); }, 'secondary'), button('Rút báo cáo', async() => { if (!confirm('Rút báo cáo này khỏi hệ thống?')) return;
                    await api('/reports/' + r.id, 'DELETE');
                    await load(); }, 'danger')); } return [$('div', {}, $('div', { class: 'target' }, r.target), $('div', { class: 'muted' }, isAdmin ? r.username : date(r.created_at))), r.description, $('div', {}, badge(r.status), $('p', { class: 'muted' }, r.admin_note)), actions]; })) : $('div', { class: 'empty' }, 'Chưa có báo cáo trong danh sách.'), pager(response.total, offset, 20, async next => { offset = next;
            await load(); }))) }
    await load();
}

function pager(total, offset, limit, load) { const prev = button('← Trước', () => load(Math.max(0, offset - limit)), 'secondary');
    prev.disabled = offset === 0; const next = button('Sau →', () => load(offset + limit), 'secondary');
    next.disabled = offset + limit >= total; return $('div', { class: 'row between' }, $('span', { class: 'muted' }, `${total?offset+1:0}–${Math.min(total,offset+limit)} / ${total}`), $('div', { class: 'actions' }, prev, next)); }
async function historyView(view) { heading(view, 'Lịch sử kiểm tra', 'Xem lại kết quả chỉ thuộc tài khoản của bạn hoặc xóa những nội dung không muốn lưu.'); const list = $('div'),
        detail = $('div');
    view.append(list, detail); let offset = 0;
    async function load() { const r = await api('/checks?offset=' + offset);
        list.replaceChildren(card('', r.items.length ? table(['Thời gian', 'Nội dung', 'Cảnh báo', 'Thao tác'], r.items.map(x => { const input = JSON.parse(x.input_text); return [date(x.created_at), (input.text || input.urls.join(', ')).slice(0, 150), x.alert ? 'Có' : 'Chưa phát hiện', $('div', {}, button('Xem lại', async() => { const d = await api('/checks/' + x.id);
                renderResult(detail, d.result);
                detail.scrollIntoView({ behavior: 'smooth' }); }, 'secondary'), button('Xóa', async() => { if (confirm('Xóa lần kiểm tra này?')) { await api('/checks/' + x.id, 'DELETE');
                    detail.replaceChildren();
                    await load(); } }, 'danger'))]; })) : $('div', { class: 'empty' }, 'Chưa có lịch sử kiểm tra.'), pager(r.total, offset, 20, async next => { offset = next;
            await load(); }))) }
    await load(); }
async function statsView(view) { const adminView = page === 'admin_stats';
    heading(view, adminView ? 'Tổng quan hệ thống' : 'Hoạt động của tôi', 'Thống kê theo ngày, tuần hoặc tháng · Múi giờ Việt Nam · Biểu thống kê 365 ngày gần nhất.'); const period = $('select', { class: 'filter', 'aria-label': 'Khoảng thống kê', onchange: safe(load) }, [
        ['day', 'Theo ngày'],
        ['week', 'Theo tuần'],
        ['month', 'Theo tháng']
    ].map(([v, l]) => $('option', { value: v }, l))); const output = $('div');
    view.append(period, output);
    async function load() { const r = await api((adminView ? '/admin/stats' : '/stats') + '?period=' + period.value);
        output.replaceChildren($('div', { class: 'metrics' }, [
            ['checks', 'Lần kiểm tra'],
            ['alerts', 'Lần có cảnh báo'],
            ['reports', 'Báo cáo'],
            ['pending', 'Đang chờ duyệt']
        ].map(([k, l]) => card('', $('div', { class: 'metric' }, $('span', {}, l), $('strong', {}, r.totals[k]))))), card('Lượt kiểm tra', r.checks.length ? table(['Thời gian', 'Tổng số', 'Có cảnh báo', 'Tỷ lệ cảnh báo'], r.checks.map(x => [x.bucket, x.total, x.alerts, $('progress', { max: x.total, value: x.alerts, title: (100 * x.alerts / x.total).toFixed(1) + '%' })])) : $('div', { class: 'empty' }, 'Chưa có dữ liệu kiểm tra.')), card('Báo cáo được gửi', r.reports.length ? table(['Thời gian gửi', 'Số báo cáo', 'Hiện đã duyệt'], r.reports.map(x => [x.bucket, x.total, x.approved])) : $('div', { class: 'empty' }, 'Chưa có báo cáo.'))); }
    await load(); }
async function usersView(view) { heading(view, 'Quản lý người dùng', 'Khóa tài khoản hoặc thay đổi vai trò. Thay đổi quyền sẽ thu hồi các phiên đăng nhập cũ.'); const list = $('div');
    view.append(list); let offset = 0;
    async function load() { const r = await api('/admin/users?offset=' + offset);
        list.replaceChildren(card('', table(['Tài khoản', 'Vai trò', 'Trạng thái', 'Thao tác'], r.items.map(u => [u.username, u.role, u.active ? 'Hoạt động' : 'Đã khóa', u.id === me.id ? 'Tài khoản hiện tại' : $('div', {}, button(u.active ? 'Khóa' : 'Mở khóa', async() => { if (confirm('Xác nhận đổi trạng thái ' + u.username + '?')) { await api('/admin/users/' + u.id, 'PATCH', { active: !u.active, role: u.role });
                await load(); } }, 'secondary'), button(u.role === 'admin' ? 'Chuyển thành User' : 'Cấp quyền Admin', async() => { if (confirm('Xác nhận thay đổi quyền của ' + u.username + '?')) { await api('/admin/users/' + u.id, 'PATCH', { active: !!u.active, role: u.role === 'admin' ? 'user' : 'admin' });
                await load(); } }, 'danger'))])), pager(r.total, offset, 30, async n => { offset = n;
            await load(); }))) }
    await load(); }

function accountView(view) { heading(view, 'Tài khoản', 'Đổi mật khẩu để bảo vệ lịch sử kiểm tra và báo cáo của bạn.');
    view.append(button('Đăng xuất', async() => { await api('/auth/logout', 'POST', {});
        me = null;
        auth(); }, 'secondary')); const old = $('input', { id: 'old-password', type: 'password', required: '', autocomplete: 'current-password' }),
        newp = $('input', { id: 'new-password', type: 'password', required: '', minlength: 10, autocomplete: 'new-password' });
    view.append(card('Đổi mật khẩu', $('form', { onsubmit: safe(async e => { e.preventDefault();
            await api('/auth/password', 'POST', { current_password: old.value, new_password: newp.value });
            me = null;
            auth();
            notice('Đã đổi mật khẩu. Đăng nhập lại để tiếp tục.'); }) }, field('Mật khẩu hiện tại', old), field('Mật khẩu mới', newp), $('div', { class: 'actions' }, $('button', { type: 'submit' }, 'Đổi mật khẩu'))))) }
(async() => { try { me = await api('/auth/me');
        shell(); } catch { auth(); } })();