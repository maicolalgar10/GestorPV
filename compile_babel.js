const fs = require('fs');
const https = require('https');

function download(url, dest, cb) {
  https.get(url, (res) => {
    if (res.statusCode >= 300 && res.statusCode < 400 && res.headers.location) {
      return download(new URL(res.headers.location, url).href, dest, cb);
    }
    const file = fs.createWriteStream(dest);
    res.pipe(file);
    file.on('finish', () => { file.close(cb); });
  }).on('error', (err) => {
    console.error('Error downloading:', err);
  });
}

console.log('Downloading Babel Standalone...');
download('https://unpkg.com/@babel/standalone/babel.min.js', 'babel-standalone.js', () => {
  console.log('Downloaded babel');
  const Babel = require('./babel-standalone.js');
  
  let html = fs.readFileSync('templates/tesoreria.html', 'utf8');
  const start = html.indexOf('<script type=\"text/babel\">');
  const end = html.indexOf('</script>', start);
  
  if (start === -1) {
    console.log('No Babel script tag found.');
    return;
  }

  let rawScript = html.substring(start + 26, end);
  // Remove Jinja tags if any
  rawScript = rawScript.replace(/{%\s*raw\s*%}/g, '').replace(/{%\s*endraw\s*%}/g, '');
  
  try {
    console.log('Transforming JSX...');
    const output = Babel.transform(rawScript, { presets: ['react'] }).code;
    html = html.substring(0, start) + '<script>\n' + output + '\n</script>' + html.substring(end + 9);
    
    // Remove babel dependency tag from head
    html = html.replace(/<script src=\"https:\/\/unpkg\.com\/@babel\/standalone\/babel\.min\.js\"><\/script>\r?\n?/g, '');
    
    fs.writeFileSync('templates/tesoreria_compiled.html', html);
    fs.writeFileSync('templates/tesoreria.html', html);
    console.log('Compiled and updated tesoreria.html');
  } catch (e) {
    console.error('Error during transformation:', e);
  }
});
