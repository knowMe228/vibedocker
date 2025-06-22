const http = require('http');
const fs = require('fs');
const path = require('path');
const mysql = require('mysql2/promise');
const url = require('url');
const cookie = require('cookie');

const PORT = 80;

const dbConfig = {
  host: 'db',
  user: 'root',
  password: 'root',
  database: 'lab1',
};

async function retrieveListItems() {
  const connection = await mysql.createConnection(dbConfig);
  const [rows] = await connection.execute('SELECT id, text FROM items');
  await connection.end();
  return rows;
}

async function getHtmlRows() {
  const rows = await retrieveListItems();
  return rows.map((item, index) => `
    <tr>
      <td>${index + 1}</td>
      <td>${item.text}</td>
      <td>
        <button onclick="editItem(${item.id})">редактировать</button>
        <button onclick="deleteItem(${item.id})">удалить</button>
      </td>
    </tr>
  `).join('');
}

async function addItemToDb(text) {
  const connection = await mysql.createConnection(dbConfig);
  const [result] = await connection.execute('INSERT INTO items (text) VALUES (?)', [text]);
  await connection.end();
  return { id: result.insertId, text };
}

async function deleteItemFromDb(id) {
  const connection = await mysql.createConnection(dbConfig);
  await connection.execute('DELETE FROM items WHERE id = ?', [id]);
  await connection.end();
}

async function updateItemInDb(id, newText) {
  const connection = await mysql.createConnection(dbConfig);
  await connection.execute('UPDATE items SET text = ? WHERE id = ?', [newText, id]);
  await connection.end();
}

const server = http.createServer(async (req, res) => {
  const parsedUrl = url.parse(req.url, true);
  const cookies = cookie.parse(req.headers.cookie || '');
  const isLoggedIn = cookies.auth === 'admin';

  // === LOGIN PAGE ===
  if (req.method === 'GET' && parsedUrl.pathname === '/login') {
    const loginPage = fs.readFileSync(path.join(__dirname, 'login.html'));
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(loginPage);
  }

  if (req.method === 'POST' && parsedUrl.pathname === '/login') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      const params = new URLSearchParams(body);
      const username = params.get('username');
      const password = params.get('password');

      if (username === 'admin' && password === 'admin') {
        res.writeHead(302, {
          'Set-Cookie': cookie.serialize('auth', 'admin', { httpOnly: true }),
          'Location': '/'
        });
        return res.end();
      } else {
        res.writeHead(401);
        return res.end('Unauthorized');
      }
    });
    return;
  }

  // === AUTH CHECK ===
  if (!isLoggedIn) {
    res.writeHead(302, { Location: '/login' });
    return res.end();
  }

  // === MAIN PAGE ===
  if (req.method === 'GET' && parsedUrl.pathname === '/') {
    const htmlPath = path.join(__dirname, 'index.html');
    let html = fs.readFileSync(htmlPath, 'utf8');
    const rows = await getHtmlRows();
    html = html.replace('{{rows}}', rows);
    res.writeHead(200, { 'Content-Type': 'text/html' });
    return res.end(html);
  }

  // === ADD ITEM ===
  if (req.method === 'POST' && parsedUrl.pathname === '/add-item') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      const { text } = JSON.parse(body);
      const result = await addItemToDb(text);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, item: result }));
    });
    return;
  }

  // === DELETE ITEM ===
  if (req.method === 'DELETE' && parsedUrl.pathname.startsWith('/delete-item/')) {
    const id = parsedUrl.pathname.split('/').pop();
    await deleteItemFromDb(id);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    return res.end(JSON.stringify({ success: true }));
  }

  // === EDIT ITEM ===
  if (req.method === 'PUT' && parsedUrl.pathname.startsWith('/edit-item/')) {
    const id = parsedUrl.pathname.split('/').pop();
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      const { text } = JSON.parse(body);
      await updateItemInDb(id, text);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true }));
    });
    return;
  }

  // === STATIC FILES ===
  if (req.method === 'GET') {
    const filePath = path.join(__dirname, parsedUrl.pathname);
    if (fs.existsSync(filePath)) {
      const ext = path.extname(filePath).toLowerCase();
      const contentType = ext === '.js' ? 'text/javascript' : 'text/plain';
      res.writeHead(200, { 'Content-Type': contentType });
      return res.end(fs.readFileSync(filePath));
    }
  }

  // === 404 ===
  res.writeHead(404);
  res.end('Not Found');
});

server.listen(PORT, () => {
  console.log(`Server is running on http://localhost:${PORT}`);
});
