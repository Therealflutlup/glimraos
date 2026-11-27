package de.glimraos.app

import android.annotation.SuppressLint
import android.app.Activity
import android.app.AlertDialog
import android.net.http.SslCertificate
import android.net.http.SslError
import android.webkit.SslErrorHandler
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.net.Uri
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Toast
import org.json.JSONArray
import org.json.JSONObject
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.HttpURLConnection
import java.net.InetAddress
import java.net.SocketTimeoutException
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import kotlin.concurrent.thread

/**
 * GlimraApp – steuert einen Glimra-OS-PC aus dem Heimnetz.
 * Die Oberfläche ist HTML (assets/index.html); Netzwerk, Speicher und Dateien macht Kotlin.
 */
class MainActivity : Activity() {

    private lateinit var web: WebView
    private val prefs by lazy { getSharedPreferences("glimra", Context.MODE_PRIVATE) }
    private var pickId = 0
    private var pickTarget: Pair<String, String>? = null   // host:port, token
    private var shared: JSONObject? = null
    private var sharedUri: Uri? = null

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        web = WebView(this)
        web.setBackgroundColor(Color.parseColor("#0d1020"))
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.addJavascriptInterface(Bridge(), "Glimra")
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest) = false

            // Glimra Server nutzt ein selbst erstelltes Zertifikat: beim ersten Mal fragen,
            // danach nur genau diesem Zertifikat (Fingerabdruck) vertrauen.
            override fun onReceivedSslError(view: WebView, handler: SslErrorHandler, error: SslError) {
                val host = Uri.parse(error.url).host ?: ""
                val fp = fingerprint(error.certificate)
                if (fp == null || !isLocalAddress(host)) {
                    handler.cancel()
                    return
                }
                val key = "cert:$host"
                val known = prefs.getString(key, "")
                when {
                    known == fp -> handler.proceed()
                    known.isNullOrEmpty() -> AlertDialog.Builder(this@MainActivity)
                        .setTitle("Glimra Server vertrauen?")
                        .setMessage("$host verwendet ein eigenes Zertifikat.\n\nFingerabdruck:\n$fp\n\nVergleiche ihn mit der Anzeige am Server (glimra-server-status).")
                        .setPositiveButton("Vertrauen") { _, _ -> prefs.edit().putString(key, fp).apply(); handler.proceed() }
                        .setNegativeButton("Abbrechen") { _, _ -> handler.cancel() }
                        .setOnCancelListener { handler.cancel() }
                        .show()
                    else -> AlertDialog.Builder(this@MainActivity)
                        .setTitle("Achtung: Zertifikat geändert")
                        .setMessage("Das Zertifikat von $host hat sich geändert. Wenn du den Server nicht neu eingerichtet hast, könnte jemand die Verbindung abfangen.\n\nNeuer Fingerabdruck:\n$fp")
                        .setPositiveButton("Neues Zertifikat vertrauen") { _, _ -> prefs.edit().putString(key, fp).apply(); handler.proceed() }
                        .setNegativeButton("Abbrechen") { _, _ -> handler.cancel() }
                        .setOnCancelListener { handler.cancel() }
                        .show()
                }
            }
        }
        setContentView(web)
        web.loadUrl("file:///android_asset/index.html")
        handleShare(intent)
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        handleShare(intent)
        web.evaluateJavascript("window.onShare && window.onShare()", null)
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (web.url?.startsWith("file:") == false) {
            web.loadUrl("file:///android_asset/index.html")
        } else {
            web.evaluateJavascript("window.goBack ? window.goBack() : false") { handled ->
                if (handled != "true") super.onBackPressed()
            }
        }
    }

    private fun handleShare(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        val text = intent.getStringExtra(Intent.EXTRA_TEXT)
        @Suppress("DEPRECATION")
        val uri: Uri? = intent.getParcelableExtra(Intent.EXTRA_STREAM)
        if (uri != null) {
            sharedUri = uri
            shared = JSONObject().put("type", "file").put("name", fileName(uri))
        } else if (text != null) {
            sharedUri = null
            shared = JSONObject().put("type", "text").put("text", text)
        }
    }

    private fun fingerprint(cert: SslCertificate?): String? {
        cert ?: return null
        val bytes: ByteArray? = if (Build.VERSION.SDK_INT >= 29) {
            cert.x509Certificate?.encoded
        } else {
            SslCertificate.saveState(cert).getByteArray("x509-certificate")
        }
        bytes ?: return null
        return MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(":") { "%02X".format(it) }
    }

    /** Nur Geräte im Heimnetz (private Adressen, .local) dürfen eigene Zertifikate verwenden. */
    private fun isLocalAddress(host: String): Boolean {
        if (host.endsWith(".local")) return true
        val p = host.split(".").mapNotNull { it.toIntOrNull() }
        if (p.size != 4) return false
        return p[0] == 10 || (p[0] == 172 && p[1] in 16..31) || (p[0] == 192 && p[1] == 168) || p[0] == 127
    }

    private fun callback(id: Int, status: Int, data: String) {
        val js = "window.__glimraCb($id,$status,${JSONObject.quote(data)})"
        runOnUiThread { web.evaluateJavascript(js, null) }
    }

    private fun fileName(uri: Uri): String {
        contentResolver.query(uri, null, null, null, null)?.use { c ->
            val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (idx >= 0 && c.moveToFirst()) return c.getString(idx)
        }
        return uri.lastPathSegment ?: "datei"
    }

    private fun upload(id: Int, uri: Uri, host: String, token: String) { thread {
        try {
            val name = fileName(uri)
            val size = contentResolver.query(uri, null, null, null, null)?.use { c ->
                val idx = c.getColumnIndex(OpenableColumns.SIZE)
                if (idx >= 0 && c.moveToFirst()) c.getLong(idx) else -1L
            } ?: -1L
            val conn = URL("http://$host/upload").openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.doOutput = true
            conn.connectTimeout = 5000
            conn.setRequestProperty("Authorization", "Bearer $token")
            conn.setRequestProperty("X-Filename", URLEncoder.encode(name, "UTF-8"))
            conn.setRequestProperty("Content-Type", "application/octet-stream")
            if (size > 0) {
                conn.setFixedLengthStreamingMode(size)
                contentResolver.openInputStream(uri)?.use { input ->
                    conn.outputStream.use { out -> input.copyTo(out, 1 shl 16) }
                }
            } else {
                // Größe unbekannt: erst einlesen, damit der PC die Länge kennt
                val bytes = contentResolver.openInputStream(uri)?.use { it.readBytes() } ?: ByteArray(0)
                conn.setFixedLengthStreamingMode(bytes.size)
                conn.outputStream.use { it.write(bytes) }
            }
            val code = conn.responseCode
            val body = (if (code < 400) conn.inputStream else conn.errorStream)?.bufferedReader()?.readText() ?: ""
            callback(id, code, body)
        } catch (e: Exception) {
            callback(id, 0, JSONObject().put("error", e.message ?: "Fehler").toString())
        }
    } }

    @Deprecated("Deprecated in Java")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 42) return
        val uri = data?.data
        val target = pickTarget
        if (resultCode != RESULT_OK || uri == null || target == null) {
            callback(pickId, 0, JSONObject().put("error", "abgebrochen").toString())
            return
        }
        upload(pickId, uri, target.first, target.second)
    }

    inner class Bridge {
        @android.webkit.JavascriptInterface
        fun get(key: String): String = prefs.getString(key, "") ?: ""

        @android.webkit.JavascriptInterface
        fun set(key: String, value: String) {
            prefs.edit().putString(key, value).apply()
        }

        @android.webkit.JavascriptInterface
        fun deviceName(): String = "${Build.MANUFACTURER.replaceFirstChar { it.uppercase() }} ${Build.MODEL}"

        @android.webkit.JavascriptInterface
        fun toast(text: String) {
            runOnUiThread { Toast.makeText(this@MainActivity, text, Toast.LENGTH_SHORT).show() }
        }

        @android.webkit.JavascriptInterface
        fun copy(text: String) {
            runOnUiThread {
                val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                cm.setPrimaryClip(ClipData.newPlainText("Glimra OS", text))
            }
        }

        @android.webkit.JavascriptInterface
        fun paste(): String {
            val cm = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            return cm.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)?.coerceToText(this@MainActivity)?.toString() ?: ""
        }

        /** HTTP-Anfrage an den PC (ohne CORS-Probleme). Antwort kommt über window.__glimraCb. */
        @android.webkit.JavascriptInterface
        fun http(id: Int, method: String, url: String, token: String, body: String) { thread {
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.requestMethod = method
                conn.connectTimeout = 4000
                conn.readTimeout = 15000
                conn.setRequestProperty("Content-Type", "application/json")
                if (token.isNotEmpty()) conn.setRequestProperty("Authorization", "Bearer $token")
                if (method == "POST") {
                    conn.doOutput = true
                    conn.outputStream.use { it.write(body.toByteArray()) }
                }
                val code = conn.responseCode
                val text = (if (code < 400) conn.inputStream else conn.errorStream)?.bufferedReader()?.readText() ?: ""
                callback(id, code, text)
            } catch (e: Exception) {
                val why = when (e) {
                    is java.net.ConnectException -> "Nicht erreichbar: Verbindung abgelehnt – ist die Fernsteuerung in Glimra OS an?"
                    is SocketTimeoutException -> "Nicht erreichbar: keine Antwort – gleiches WLAN? IP richtig? Firewall?"
                    is java.net.UnknownHostException -> "Nicht erreichbar: Adresse unbekannt – IP-Adresse prüfen"
                    is java.net.NoRouteToHostException -> "Nicht erreichbar: kein Weg zum PC – gleiches WLAN?"
                    else -> "Nicht erreichbar (" + e.javaClass.simpleName + ")"
                }
                callback(id, 0, JSONObject().put("error", why).toString())
            }
        } }

        /** Sucht Glimra-OS-PCs und -Server im WLAN (UDP-Broadcast auf Port 8766). */
        @android.webkit.JavascriptInterface
        fun discover(id: Int) { thread {
            val found = JSONArray()
            val seen = HashSet<String>()
            val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            val lock = wifi.createMulticastLock("glimra").apply { setReferenceCounted(false); acquire() }
            try {
                DatagramSocket().use { sock ->
                    sock.broadcast = true
                    sock.soTimeout = 400
                    val msg = "GLIMRA?".toByteArray()
                    val targets = mutableListOf(InetAddress.getByName("255.255.255.255"))
                    @Suppress("DEPRECATION")
                    val dhcp = wifi.dhcpInfo
                    if (dhcp != null && dhcp.netmask != 0) {
                        val bc = (dhcp.ipAddress and dhcp.netmask) or dhcp.netmask.inv()
                        val bytes = ByteArray(4) { k -> (bc shr (k * 8) and 0xff).toByte() }
                        targets.add(InetAddress.getByAddress(bytes))
                    }
                    repeat(2) {
                        targets.forEach { t -> sock.send(DatagramPacket(msg, msg.size, t, 8766)) }
                    }
                    val end = System.currentTimeMillis() + 1800
                    val buf = ByteArray(1024)
                    while (System.currentTimeMillis() < end) {
                        try {
                            val p = DatagramPacket(buf, buf.size)
                            sock.receive(p)
                            val o = JSONObject(String(p.data, 0, p.length))
                            val host = p.address.hostAddress ?: continue
                            val key = host + ":" + o.optInt("port")
                            if (seen.add(key)) found.put(o.put("ip", host))
                        } catch (timeout: SocketTimeoutException) {
                        }
                    }
                }
            } catch (error: Exception) {
            } finally {
                lock.release()
            }
            callback(id, 200, found.toString())
        } }

        @android.webkit.JavascriptInterface
        fun pickFile(id: Int, host: String, token: String) { runOnUiThread {
            pickId = id
            pickTarget = host to token
            val i = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = "*/*"
            }
            @Suppress("DEPRECATION")
            startActivityForResult(i, 42)
        } }

        @android.webkit.JavascriptInterface
        fun takeShare(): String {
            val s = shared?.toString() ?: ""
            shared = null
            return s
        }

        @android.webkit.JavascriptInterface
        fun uploadShared(id: Int, host: String, token: String) {
            val uri = sharedUri
            if (uri == null) callback(id, 0, JSONObject().put("error", "Keine Datei").toString())
            else { sharedUri = null; upload(id, uri, host, token) }
        }

        @android.webkit.JavascriptInterface
        fun openPanel(url: String) {
            runOnUiThread { if (url.startsWith("http://") || url.startsWith("https://")) web.loadUrl(url) }
        }
    }
}
