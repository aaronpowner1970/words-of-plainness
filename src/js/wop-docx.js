/**
 * WORDS OF PLAINNESS — Word (.docx) writer for the Reflections panel
 * ==================================================================
 *
 * CODE-SITE-18, SITE step 27, spec 3.3. Builds a .docx file in the browser from
 * the panel's export model, with no library and no network: a minimal
 * WordprocessingML package (document, styles, core properties) in an
 * uncompressed ZIP. Loaded by /js/wop-reflections-panel.js only when the reader
 * asks for a Word download. Attaches window.WopDocx.build(model) → Blob.
 */
(function () {
    'use strict';

    // ------------------------------------------------------------ XML helpers
    function esc(s) {
        return String(s == null ? '' : s)
            // characters XML 1.0 does not allow
            .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g, '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /** A run of text; line breaks and tabs inside it are kept. */
    function runs(text, rPr) {
        var props = rPr ? '<w:rPr>' + rPr + '</w:rPr>' : '';
        var lines = String(text == null ? '' : text).replace(/\r\n?/g, '\n').split('\n');
        return lines.map(function (line, i) {
            var parts = line.split('\t').map(function (seg) {
                return '<w:t xml:space="preserve">' + esc(seg) + '</w:t>';
            }).join('<w:tab/>');
            return '<w:r>' + props + (i > 0 ? '<w:br/>' : '') + parts + '</w:r>';
        }).join('');
    }

    function para(style, inner) {
        return '<w:p>' + (style ? '<w:pPr><w:pStyle w:val="' + style + '"/></w:pPr>' : '') + inner + '</w:p>';
    }

    function documentXml(m) {
        var body = [];
        body.push(para('Title', runs(m.title)));
        body.push(para('DateLine', runs(m.dateLine)));
        m.groups.forEach(function (g) {
            body.push(para('Heading1', runs(g.title)));
            g.answers.forEach(function (it) {
                body.push(para('Heading2', runs(it.section ? it.label + ' · ' + it.section : it.label)));
                if (it.prompt) body.push(para('Prompt', runs(m.promptLabel + ': ', '<w:i/>') + runs(it.prompt.replace(/\n+/g, ' '))));
                body.push(para('Words', runs(it.content)));
                if (it.written) body.push(para('Written', runs(it.written)));
            });
            if (g.questions.length) {
                body.push(para('Heading2', runs(m.questionsHeading)));
                g.questions.forEach(function (it) {
                    body.push(para('Words', runs(it.content)));
                    if (it.written) body.push(para('Written', runs(it.written)));
                });
            }
        });
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
            '<w:body>' + body.join('') +
            '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/>' +
            '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>' +
            '</w:body></w:document>';
    }

    function style(id, name, pPr, rPr, basedOn) {
        return '<w:style w:type="paragraph" w:styleId="' + id + '"><w:name w:val="' + name + '"/>' +
            (basedOn ? '<w:basedOn w:val="' + basedOn + '"/>' : '') + '<w:qFormat/>' +
            (pPr ? '<w:pPr>' + pPr + '</w:pPr>' : '') + (rPr ? '<w:rPr>' + rPr + '</w:rPr>' : '') + '</w:style>';
    }

    var FONT = '<w:rFonts w:ascii="Georgia" w:hAnsi="Georgia" w:eastAsia="Georgia" w:cs="Georgia"/>';
    var STYLES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' +
        '<w:docDefaults><w:rPrDefault><w:rPr>' + FONT + '<w:sz w:val="22"/><w:szCs w:val="22"/><w:lang w:val="en-US"/></w:rPr></w:rPrDefault>' +
        '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>' +
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>' +
        style('Title', 'Title', '<w:spacing w:after="60"/>', '<w:b/><w:sz w:val="36"/><w:szCs w:val="36"/>', 'Normal') +
        style('DateLine', 'Date Line', '<w:spacing w:after="280"/>', '<w:color w:val="555555"/><w:sz w:val="20"/>', 'Normal') +
        style('Heading1', 'heading 1', '<w:keepNext/><w:spacing w:before="320" w:after="120"/><w:outlineLvl w:val="0"/>', '<w:b/><w:sz w:val="28"/><w:szCs w:val="28"/>', 'Normal') +
        style('Heading2', 'heading 2', '<w:keepNext/><w:spacing w:before="220" w:after="60"/><w:outlineLvl w:val="1"/>', '<w:b/><w:sz w:val="23"/><w:szCs w:val="23"/>', 'Normal') +
        style('Prompt', 'Prompt', '<w:spacing w:after="80"/>', '<w:color w:val="444444"/><w:sz w:val="20"/>', 'Normal') +
        style('Words', 'Words', '<w:spacing w:after="80"/>', '', 'Normal') +
        style('Written', 'Written', '<w:spacing w:after="160"/>', '<w:i/><w:color w:val="666666"/><w:sz w:val="18"/>', 'Normal') +
        '</w:styles>';

    var CONTENT_TYPES = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
        '<Default Extension="xml" ContentType="application/xml"/>' +
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
        '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
        '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
        '</Types>';

    var ROOT_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>' +
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
        '</Relationships>';

    var DOC_RELS = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
        '</Relationships>';

    function coreXml(m) {
        var now = new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
        return '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" ' +
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">' +
            '<dc:title>' + esc(m.title) + '</dc:title>' +
            '<dcterms:created xsi:type="dcterms:W3CDTF">' + now + '</dcterms:created>' +
            '<dcterms:modified xsi:type="dcterms:W3CDTF">' + now + '</dcterms:modified>' +
            '</cp:coreProperties>';
    }

    // ------------------------------------------------------------ ZIP (stored, no compression)
    var CRC_TABLE = (function () {
        var t = new Uint32Array(256);
        for (var n = 0; n < 256; n++) {
            var c = n;
            for (var k = 0; k < 8; k++) c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
            t[n] = c >>> 0;
        }
        return t;
    })();

    function crc32(bytes) {
        var c = 0xFFFFFFFF;
        for (var i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
        return (c ^ 0xFFFFFFFF) >>> 0;
    }

    function utf8(s) { return new TextEncoder().encode(s); }

    function zip(files) {
        var now = new Date();
        var dosTime = ((now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1)) & 0xFFFF;
        var dosDate = (((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate()) & 0xFFFF;
        var chunks = [], central = [], offset = 0;

        files.forEach(function (f) {
            var name = utf8(f.name), data = utf8(f.data), crc = crc32(data);
            var lh = new DataView(new ArrayBuffer(30));
            lh.setUint32(0, 0x04034b50, true);
            lh.setUint16(4, 20, true);          // version needed
            lh.setUint16(6, 0x0800, true);      // UTF-8 names
            lh.setUint16(8, 0, true);           // stored
            lh.setUint16(10, dosTime, true);
            lh.setUint16(12, dosDate, true);
            lh.setUint32(14, crc, true);
            lh.setUint32(18, data.length, true);
            lh.setUint32(22, data.length, true);
            lh.setUint16(26, name.length, true);
            lh.setUint16(28, 0, true);
            chunks.push(new Uint8Array(lh.buffer), name, data);

            var ch = new DataView(new ArrayBuffer(46));
            ch.setUint32(0, 0x02014b50, true);
            ch.setUint16(4, 20, true);          // version made by
            ch.setUint16(6, 20, true);          // version needed
            ch.setUint16(8, 0x0800, true);
            ch.setUint16(10, 0, true);
            ch.setUint16(12, dosTime, true);
            ch.setUint16(14, dosDate, true);
            ch.setUint32(16, crc, true);
            ch.setUint32(20, data.length, true);
            ch.setUint32(24, data.length, true);
            ch.setUint16(28, name.length, true);
            ch.setUint16(30, 0, true);          // extra
            ch.setUint16(32, 0, true);          // comment
            ch.setUint16(34, 0, true);          // disk
            ch.setUint16(36, 0, true);          // internal attrs
            ch.setUint32(38, 0, true);          // external attrs
            ch.setUint32(42, offset, true);
            central.push(new Uint8Array(ch.buffer), name);

            offset += 30 + name.length + data.length;
        });

        var cdSize = central.reduce(function (n, c) { return n + c.length; }, 0);
        var end = new DataView(new ArrayBuffer(22));
        end.setUint32(0, 0x06054b50, true);
        end.setUint16(4, 0, true);
        end.setUint16(6, 0, true);
        end.setUint16(8, files.length, true);
        end.setUint16(10, files.length, true);
        end.setUint32(12, cdSize, true);
        end.setUint32(16, offset, true);
        end.setUint16(20, 0, true);

        return new Blob(chunks.concat(central, [new Uint8Array(end.buffer)]), {
            type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        });
    }

    window.WopDocx = {
        build: function (model) {
            return zip([
                { name: '[Content_Types].xml', data: CONTENT_TYPES },
                { name: '_rels/.rels', data: ROOT_RELS },
                { name: 'docProps/core.xml', data: coreXml(model) },
                { name: 'word/_rels/document.xml.rels', data: DOC_RELS },
                { name: 'word/styles.xml', data: STYLES },
                { name: 'word/document.xml', data: documentXml(model) }
            ]);
        },
        // exposed for tests
        _documentXml: documentXml
    };
})();
