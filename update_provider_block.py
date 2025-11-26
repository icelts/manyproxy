# -*- coding: utf-8 -*-
from pathlib import Path
path = Path('frontend/pages/admin.html')
text = path.read_text(encoding='utf-8')
old = "                        <div class=\"col-md-6\">\r\n                            <div class=\"form-group\" id=\"providerField\">\r\n                                <label for=\"productProvider\">�ṩ�� <span class=\"text-danger\">*</span></label>\r\n                                <input type=\"text\" id=\"productProvider\" class=\"form-control\" placeholder=\"��: Viettel, FPT, VNPT\" required>\r\n                            </div>\r\n                                <small id=\"providerHelpText\" class=\"form-text text-muted d-none\">?????????????????????????</small>\r\n                        </div>"
new = "                        <div class=\"col-md-6\">\r\n                            <div class=\"form-group\" id=\"providerField\">\r\n                                <label for=\"productProvider\">提供商 <span class=\"text-danger\">*</span></label>\r\n                                <input type=\"text\" id=\"productProvider\" class=\"form-control\" placeholder=\"如：Viettel, FPT, VNPT\" required>\r\n                                <small id=\"providerHelpText\" class=\"form-text text-muted d-none\">静态代理的运营商由客户下单时选择，此处无需预设。</small>\r\n                            </div>\r\n                        </div>"
if old not in text:
    raise SystemExit('provider block not found')
text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
