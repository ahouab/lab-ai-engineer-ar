<div dir="rtl" lang="ar">

# مختبر هندسة الذكاء الاصطناعي على حاسوب Ryzen مصغّر

في هذا المختبر، تشغّل نموذجًا لغويًا محليًا على حاسوبك المصغّر وتستخدمه من حاسوب محمول أو هاتف. مشروع التدريب هو مساعد يجيب بالعربية استنادًا إلى أدلة تشغيل تقنية ويستشهد بالمقاطع التي اعتمد عليها. أُعدّت الخطوات لجهاز Ryzen 5000 بذاكرة 32 غيغابايت وقرص 500 غيغابايت. تحقّق أولًا من طراز المعالج ونوع القرص ووجود بطاقة رسومات منفصلة.

يستخدم [مسار هندسة الذكاء الاصطناعي على مدى ثلاثة أيام](FORMATION.md) هذا المختبر في التمارين.

## البنية والموارد المطلوبة

<div dir="ltr">

~~~mermaid
flowchart RL
    Laptop["حاسوب محمول أو هاتف"] -->|"Tailscale · HTTPS"| UI["Open WebUI"]
    Laptop -->|"Tailscale · SSH"| API["واجهة FastAPI"]
    UI --> LLM["Ollama · Qwen3 + BGE-M3"]
    API --> LLM
    API --> DB["Qdrant · فهرس أدلة التشغيل"]
    Docs["PDF نصي وMarkdown وTXT"] -->|"فهرسة محلية"| DB
~~~

</div>

| المكوّن | الإعداد المبدئي |
| --- | --- |
| النظام | استخدم Ubuntu Server 24.04 LTS داخل آلة افتراضية إذا كان جهازك يعمل بـ Proxmox. يمكنك أيضًا تثبيت Ubuntu مباشرة على الجهاز. |
| الآلة الافتراضية `lab-ai-ar` | خصّص 6 معالجات افتراضية إذا سمحت موارد المضيف، وذاكرة ثابتة بسعة 16 غيغابايت، وقرص VirtIO SCSI بسعة 100 إلى 120 غيبيبايت، وبطاقة شبكة VirtIO على الجسر `vmbr0`. |
| الاستدلال | استخدم المعالج المركزي وسياقًا بطول 4,096 رمزًا. شغّل طلب توليد واحدًا في كل مرة لكل نموذج. يمكن إبقاء نموذجين محمّلين إذا سمحت الذاكرة. |
| النماذج | استخدم `qwen3:4b` للإجابة و`bge-m3:latest` للفهرسة. جرّب `qwen3:8b` للمقارنة بعد قياس أداء النموذج الأول. |
| الوصول | استخدم Open WebUI عبر HTTPS على شبكتك الخاصة في Tailscale، ومفتاح SSH مع أنفاق للوصول إلى واجهات البرمجة. |

أوزان النموذجين المدرّبين مسبقًا `qwen3:4b` و`qwen3:8b` متاحة بموجب رخصة Apache 2.0. تستضيف الأوزان وتشغّل الاستدلال على جهازك. تبلغ أحجام تنزيل النسختين بتكميم Q4_K_M نحو **2.5 غيغابايت** و**5.2 غيغابايت**. يتطلب نموذج التضمين متعدد اللغات `bge-m3`، المتاح بموجب رخصة MIT، نحو **1.2 غيغابايت** إضافية. يدخل السياق والخدمات أيضًا في استهلاك الذاكرة. قِس زمن الاستجابة وجودتها على جهازك لتحديد جدوى النموذج 8B. [Qwen3 4B](https://ollama.com/library/qwen3:4b)، [Qwen3 8B](https://ollama.com/library/qwen3:8b)، [BGE-M3 في Ollama](https://ollama.com/library/bge-m3)، [بطاقة نموذج BGE-M3 ورخصته](https://huggingface.co/BAAI/bge-m3).

تعالج مكوّنات الحاسوب المصغّر المحادثات والمستندات وحساب التضمينات وتوليد الإجابات. تحتاج عملية التثبيت والتحديث إلى تنزيل صور الحاويات والنماذج. تتولّى Tailscale تنسيق اتصالات الشبكة الخاصة. [التشغيل المحلي في Ollama](https://docs.ollama.com/faq)، [خدمة Tailscale Serve](https://tailscale.com/docs/features/tailscale-serve).

## 1. تجهيز الحاسوب المصغّر

تحقّق من موارد **الجهاز الفعلي** والآلات الافتراضية الموجودة عليه.

<div dir="ltr">

~~~bash
lscpu
free -h
lsblk -d -o NAME,SIZE,ROTA,MODEL
~~~

</div>

يشير `ROTA=0` عادةً إلى قرص SSD، بما في ذلك أقراص NVMe، ويشير `ROTA=1` إلى قرص ميكانيكي. توقّع وقتًا أطول لتحميل النماذج وفهرسة المستندات على القرص الميكانيكي. صِل الجهاز بالشبكة عبر إيثرنت وعطّل وضع السكون ليبقى متاحًا.

- **إذا كان Proxmox مثبتًا.** راجع الذاكرة ومساحة التخزين المتاحتين في تبويب **Summary**. أنشئ الآلة الافتراضية `lab-ai-ar` من صورة Ubuntu Server 24.04 للمعمارية amd64. في إعدادات **CPU** اختر النوع `host`. عطّل تغيير حجم الذاكرة تلقائيًا (ballooning)، وفعّل خياري **QEMU Guest Agent** و**Start at boot**. استخدم جسر الشبكة المحلية الموجود، وهو عادةً `vmbr0`. اترك نحو 30 إلى 50 غيبيبايت من المساحة الفعلية على المضيف بعد التخصيص. إذا كانت هناك آلات افتراضية أخرى قيد التشغيل، فابدأ بأربعة معالجات افتراضية و12 غيغابايت من الذاكرة مع النموذج 4B، ثم زِد التخصيص حسب الموارد المتاحة. [إدارة الآلات الافتراضية في Proxmox](https://github.com/proxmox/pve-docs/blob/master/qm.adoc).
- **إذا كان Ubuntu 24.04 مثبتًا، أو قرّرت تثبيته مباشرةً.** انتقل إلى خطوة تجهيز Ubuntu. يمكنك كذلك تثبيت Proxmox على قرص فارغ ثم إنشاء آلة افتراضية. قبل أي تثبيت جديد، انسخ بياناتك احتياطيًا وتحقّق من القرص المحدّد في برنامج التثبيت. [صورة Ubuntu Server 24.04](https://releases.ubuntu.com/24.04/)، [صورة Proxmox VE](https://www.proxmox.com/en/downloads/proxmox-virtual-environment/iso).

### تجهيز Ubuntu ومفتاح SSH

في برنامج التثبيت، اضبط اسم الجهاز على `lab-ai-ar`، وأنشئ الحساب `labadmin`، وحدّد **Install OpenSSH server**. يمكنك حجز عنوان DHCP لهذا الجهاز على الموجّه لتسهيل العثور عليه. العنوان `192.168.1.60` في الأمثلة عنوان توضيحي. استبدله بعنوان جهاز Ubuntu الذي يعرضه الأمر `ip -br -4 addr`.

نفّذ الأوامر التالية في Ubuntu سواء كان داخل آلة افتراضية أم مثبتًا مباشرة على الجهاز.

<div dir="ltr">

~~~bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y ca-certificates curl git jq openssh-server openssl unzip python3-venv
ip -br -4 addr
free -h
df -h /
~~~

</div>

عند استخدام LVM لقسم الجذر، تحقّق عبر `df -h /` من أن مساحة الجذر تكفي لصور Docker والنماذج والفهارس. توفّر مساحة تقارب 80 غيبيبايت أو أكثر هامشًا مناسبًا في آلة افتراضية جديدة. قد يخصّص برنامج التثبيت جزءًا فقط من مجموعة وحدات التخزين لقسم الجذر.

داخل آلة Proxmox الافتراضية، ثبّت الوكيل بالأمر `sudo apt install -y qemu-guest-agent`. إذا بقي غير متاح، فأوقف الآلة وأعد تشغيلها بعد تفعيل خيار **QEMU Guest Agent** في Proxmox.

على **الحاسوب المحمول** استخدم زوج مفاتيح موجودًا، أو أنشئه بالأمر `ssh-keygen -t ed25519`. افتح طرفية Ubuntu بالحساب `labadmin`، وأضف محتوى ملف المفتاح العام ذي الامتداد `.pub` في سطر واحد إلى `~/.ssh/authorized_keys`. اختبر الاتصال من الحاسوب المحمول.

<div dir="ltr">

~~~bash
# داخل Ubuntu
install -d -m 700 ~/.ssh
touch ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
nano ~/.ssh/authorized_keys

# من الحاسوب المحمول
ssh -o PreferredAuthentications=publickey labadmin@192.168.1.60
~~~

</div>

بعد التأكد من نجاح الدخول بالمفتاح، أبقِ الجلسة الأولى مفتوحة. طبّق الإعدادات التالية في Ubuntu، ثم اختبر الدخول مجددًا من طرفية أخرى.

<div dir="ltr">

~~~bash
sudo tee /etc/ssh/sshd_config.d/00-lab-ai-ar.conf >/dev/null <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
EOF
sudo sshd -t && sudo systemctl reload ssh
~~~

</div>

## 2. تثبيت Docker وتشغيل المحادثة المحلية

إذا كان Docker Engine وملحق Compose مثبتين على **Ubuntu 24.04**، فتحقّق من الإصدارين وتجاوز إضافة المستودع. استخدم Docker Engine 28 أو أحدث لضمان السلوك الموثّق للمنافذ المربوطة بعنوان `127.0.0.1`. إذا بدأت من نظام جديد، فثبّت الحزم الرسمية التالية. [تثبيت Docker على Ubuntu](https://docs.docker.com/engine/install/ubuntu/)، [ربط منافذ Docker](https://docs.docker.com/engine/network/port-publishing/).

<div dir="ltr">

~~~bash
sudo install -d -m 0755 /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: noble
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
~~~

</div>

### تنزيل ملفات المختبر من GitHub

من الحاسوب المحمول، افتح المستودع باستخدام حساب GitHub المصرّح له واختر **Code → Download ZIP**. من مجلّد التنزيل، انقل الأرشيف إلى Ubuntu باستخدام `scp`. ثم فكّه على Ubuntu عند التثبيت لأول مرة.

<div dir="ltr">

~~~bash
# من الحاسوب المحمول
scp lab-ai-engineer-ar-main.zip labadmin@192.168.1.60:~/

# داخل Ubuntu
cd ~
unzip lab-ai-engineer-ar-main.zip
mv -T lab-ai-engineer-ar-main lab-ai-ar
~~~

</div>

إذا كان جهاز Ubuntu يستخدم مفتاح SSH مصرّحًا له بالوصول إلى المستودع على GitHub وكان المسار `~/lab-ai-ar` متاحًا، يمكنك استنساخ المستودع مباشرةً.

<div dir="ltr">

~~~bash
git clone git@github.com:ahouab/lab-ai-engineer-ar.git ~/lab-ai-ar
~~~

</div>

نفّذ أوامر Compose من مجلّد `~/lab-ai-ar`. يُنشئ الأمر التالي ملف `.env` عند الحاجة، ويضع فيه مفتاحًا سرّيًا تحتفظ به واجهة المحادثة لتثبيت جلساتها عبر إعادة التشغيل.

إذا شغّلت المختبر الفرنسي والمختبر العربي على نظام Ubuntu نفسه، فأوقف النسخة الأخرى قبل البدء لأنهما يستخدمان المنافذ المحلية نفسها. يمكن تشغيلهما على آلتين افتراضيتين منفصلتين إذا سمحت موارد المضيف.

<div dir="ltr">

~~~bash
chmod 700 ~/lab-ai-ar
cd ~/lab-ai-ar
(umask 077; test -e .env || printf 'WEBUI_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env)
sudo docker compose config --quiet
sudo docker compose up -d ollama webui
sudo docker compose exec ollama ollama pull qwen3:4b
sudo docker compose exec ollama ollama list
curl -fsS http://127.0.0.1:11434/api/tags | jq
curl -fsS http://127.0.0.1:3000/health
~~~

</div>

إذا تعذّر الاختبار الأخير أثناء الإقلاع، فتحقّق من جاهزية خادم الويب عبر `sudo docker compose logs --tail=40 webui` ثم أعد الاختبار. يستخدم المختبر إصدارات محدّدة من صور الحاويات في [ملف Compose](compose.yaml). [تشغيل Ollama على Docker](https://docs.ollama.com/docker)، [بدء استخدام Open WebUI](https://docs.openwebui.com/getting-started/quick-start/).

من **الحاسوب المحمول**، افتح نفقًا مؤقتًا لكي تنشئ حساب مدير Open WebUI.

<div dir="ltr">

~~~bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:3000:127.0.0.1:3000 labadmin@192.168.1.60
~~~

</div>

افتح [واجهة المحادثة المحلية](http://127.0.0.1:3000) وأنشئ حساب المدير. في **Admin Panel → Settings → Authentication**، تأكّد من تعطيل التسجيلات الجديدة. اختر `qwen3:4b` في محادثة واسأله «اشرح في ثلاث نقاط دور فحص الجاهزية في Kubernetes». أثناء التوليد أو بعده، يفترض أن يُظهر الأمر `sudo docker compose exec ollama ollama ps` أن النموذج محمّل على المعالج المركزي. أغلق النفق المؤقت بـ `Ctrl+C`. [ربط Open WebUI بـ Ollama](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/).

يضبط المختبر العربية كلغة افتراضية لواجهة Open WebUI. إذا احتفظ المتصفح باختيار لغة سابق، فاختر العربية من إعدادات الواجهة أو افتح الرابط بإضافة `?lang=ar`. قد تعرض الواجهة بعض التسميات بالإنجليزية. [إعداد اللغة الافتراضية في Open WebUI](https://docs.openwebui.com/reference/env-configuration/#default_locale).

### إنشاء مساعدك المحلي

يضبط ملف [تعريف النموذج](Modelfile) مساعدًا يجيب بالعربية ويستند إلى Qwen3. يمكنك تتبّع تعديلات تعليمات النظام ومعاملات التوليد في Git.

<div dir="ltr">

~~~bash
sudo docker compose cp Modelfile ollama:/tmp/Modelfile
sudo docker compose exec ollama ollama create assistant-runbooks -f /tmp/Modelfile
sudo docker compose exec ollama ollama run assistant-runbooks --think=false "اشرح الفرق بين RTO وRPO."
~~~

</div>

حدّث صفحة Open WebUI واختر `assistant-runbooks`. يستخدم هذا التخصيص أوزان النموذج الأساسي نفسها. [مرجع Modelfile](https://docs.ollama.com/modelfile).

إذا كان لديك نموذج بصيغة GGUF متوافق مع Ollama، يمكنك استيراده. انسخ ملف النموذج بالأمر `sudo docker compose cp modele.gguf ollama:/tmp/modele.gguf`، ثم ضع `FROM /tmp/modele.gguf` في نسخة من ملف التعريف وأنشئ النموذج باسم جديد. [استيراد نموذج GGUF](https://docs.ollama.com/modelfile#build-from-a-gguf-model).

## 3. الوصول عن بُعد

### إعداد الشبكة الخاصة

ثبّت Tailscale في **Ubuntu 24.04** وضمّ الحاسوب المصغّر إلى شبكتك الخاصة، التي تسمّى *tailnet*. افتح رابط تسجيل الدخول الذي يعرضه الأمر وأكمل التسجيل بحسابك. ثبّت تطبيق Tailscale على الحاسوب المحمول أو الهاتف، ثم سجّل دخوله إلى الشبكة الخاصة نفسها. [مستودع Tailscale لـ Ubuntu 24.04](https://pkgs.tailscale.com/stable/#ubuntu-noble)، [تطبيقات Tailscale](https://tailscale.com/download).

<div dir="ltr">

~~~bash
sudo install -d -m 0755 /usr/share/keyrings
sudo curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg -o /usr/share/keyrings/tailscale-archive-keyring.gpg
sudo curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.tailscale-keyring.list -o /etc/apt/sources.list.d/tailscale.list
sudo apt update
sudo apt install -y tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up --hostname=lab-ai-ar
tailscale status
tailscale ip -4
~~~

</div>

**للمحادثة**، أتح المنفذ المحلي لأعضاء الشبكة الخاصة عبر Tailscale Serve بعد إنشاء حساب Open WebUI. إذا طلبت منك Tailscale ذلك، فعّل **MagicDNS** و**HTTPS Certificates** من إعدادات DNS. يظهر اسم DNS للحاسوب المصغّر في سجلات شفافية الشهادات بعد إصدار شهادة TLS. يمكنك استخدام نفق SSH للمحادثة إن أردت تفادي تسجيل الاسم. [أمر Serve](https://tailscale.com/docs/reference/tailscale-cli/serve)، [شهادات HTTPS وأسماء DNS](https://tailscale.com/docs/how-to/set-up-https-certificates).

<div dir="ltr">

~~~bash
sudo tailscale serve --bg http://127.0.0.1:3000
tailscale serve status
~~~

</div>

على **الحاسوب المحمول أو الهاتف**، افتح عنوان HTTPS كما ظهر من الأمر، مثل `https://lab-ai-ar.example.ts.net`. اختبر الوصول من بيانات الهاتف عبر 4G أو 5G مع تشغيل Tailscale، ثم أعد الاختبار بعد إيقافه. يفترض أن تكون الواجهة متاحة للأجهزة المصرّح لها. يعتمد هذا الإعداد على الشبكة الخاصة بدل تحويل منافذ الموجّه أو إتاحة الخدمة للإنترنت بواسطة Tailscale Funnel.

**للدخول عبر SSH**، استخدم من الحاسوب المحمول اسم MagicDNS أو عنوان IP الذي أعاده `tailscale ip -4`. في شبكة Tailscale مشتركة، اضبط قواعد الوصول كي تقتصر اتصالات SSH وHTTPS على الحسابات أو الأجهزة المصرّح لها. [MagicDNS](https://tailscale.com/docs/features/magicdns)، [قواعد الوصول في Tailscale](https://tailscale.com/docs/features/access-control/grants).

<div dir="ltr">

~~~bash
ssh labadmin@lab-ai-ar
~~~

</div>

في آلة افتراضية مخصّصة للمختبر، يمكنك قصر SSH على الشبكة المحلية وTailscale باستخدام UFW. نفّذ الإعداد من طرفية الآلة الافتراضية واضبط الشبكة الفرعية المثال بما يناسبك، ثم أعد اختبار الاتصال من الشبكتين. إذا كان لديك جدار حماية مفعّل، فأدمج القواعد في إعداده. [جدار الحماية في Ubuntu](https://documentation.ubuntu.com/server/how-to/security/firewalls/).

<div dir="ltr">

~~~bash
sudo apt install -y ufw
sudo ufw allow from 192.168.1.0/24 to any port 22 proto tcp
sudo ufw allow in on tailscale0 to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
~~~

</div>

### الوصول إلى واجهات البرمجة من الحاسوب المحمول

بعد تشغيل RAG في الخطوة التالية، افتح هذا النفق واتركه قيد التشغيل لاستخدام واجهتَي البرمجة من الطرفية أو بيئة التطوير. يمكنك استخدام عنوان الشبكة المحلية عند العمل من المنزل. للوصول إلى المحادثة عبر SSH أيضًا، أضف `-L 127.0.0.1:3000:127.0.0.1:3000` وافتح واجهة المحادثة المحلية. [واجهة المحادثة المحلية](http://127.0.0.1:3000).

<div dir="ltr">

~~~bash
ssh -N -o ExitOnForwardFailure=yes -L 127.0.0.1:8001:127.0.0.1:8001 -L 127.0.0.1:11434:127.0.0.1:11434 labadmin@lab-ai-ar
~~~

</div>

| الخدمة من الحاسوب المحمول | العنوان بعد فتح النفق |
| --- | --- |
| التوثيق التفاعلي لـ RAG | [واجهة التوثيق](http://127.0.0.1:8001/docs) |
| واجهة RAG | `http://127.0.0.1:8001/ask` و`http://127.0.0.1:8001/search` |
| واجهة Ollama | `http://127.0.0.1:11434/api/chat` |

تعتمد واجهتا RAG وOllama على مصادقة SSH في هذا الاستخدام الشخصي. يربط Compose المنافذ المنشورة بعنوان الحلقة المحلية فقط، وتبقى Qdrant داخل شبكة Docker الخاصة بخدمات RAG. تستدعي واجهة توثيق FastAPI موارد العرض من شبكة توزيع محتوى (CDN). يمكنك استدعاء الواجهة مباشرةً من دون هذه الموارد باستخدام `curl`. [توثيق FastAPI](https://fastapi.tiangolo.com/how-to/custom-docs-ui-assets/).

<a name="rag"></a>

## 4. فهرسة أدلة التشغيل وطرح الأسئلة

في Ubuntu، نزّل نموذج التضمين (embedding) الذي يستخدمه المساران التاليان.

<div dir="ltr">

~~~bash
sudo docker compose exec ollama ollama pull bge-m3
~~~

</div>

**من المتصفح.** أرفق الملف `corpus/sauvegarde.md` مثلًا بمحادثة في Open WebUI واسأل عن موعد النسخ الاحتياطي. تستخدم الواجهة فهرس المستندات الخاص بها، وتحسب التضمينات عبر Ollama وفق إعدادات Compose. [استخدام RAG مع المستندات في Open WebUI](https://docs.openwebui.com/features/chat-conversations/rag/).

**من واجهة البرمجة.** شغّل ملف تعريف RAG داخل Ubuntu لتتتبّع المقاطع والمتجهات ونتائج البحث بنفسك. تضم مجموعة المستندات أدلة تشغيل افتراضية مكتوبة بالعربية.

<div dir="ltr">

~~~bash
cd ~/lab-ai-ar
sudo docker compose --profile rag up -d --build
curl -fsS http://127.0.0.1:8001/healthz
sudo docker compose --profile rag exec -T rag python rag.py
curl -fsS http://127.0.0.1:8001/readyz
~~~

</div>

إذا لم تستجب نقطة `/healthz` أو كان Qdrant لا يزال في مرحلة الإقلاع، فراجع `sudo docker compose --profile rag ps` ثم أعد المحاولة. تنشئ الفهرسة مجموعة جديدة وتفعّلها عند اكتمال المعالجة. يُركَّب المجلّد `corpus/` داخل حاوية الواجهة في وضع القراءة فقط.

نفّذ الاختبارات التالية في Ubuntu، أو من الحاسوب المحمول أثناء فتح النفق. على Windows، يمكنك استخدام `curl.exe` أو خيار **Try it out** في [توثيق FastAPI التفاعلي](http://127.0.0.1:8001/docs).

<div dir="ltr">

~~~bash
curl -fsS http://127.0.0.1:8001/search -H 'Content-Type: application/json' -d '{"question":"في أي يوم وفي أي ساعة يبدأ النسخ الاحتياطي الكامل لمختبر أستر؟"}' | jq
curl -fsS --max-time 510 http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"في أي يوم وفي أي ساعة يبدأ النسخ الاحتياطي الكامل لمختبر أستر؟"}' | jq '{verdict, answer, sources, retrieval_ms, generation_ms}'
curl -fsS --max-time 510 http://127.0.0.1:8001/ask -H 'Content-Type: application/json' -d '{"question":"في أي منطقة من مناطق AWS تقع مجموعة الإنتاج لمختبر أستر؟"}' | jq '{verdict, answer, sources}'
~~~

</div>

يعرض الطلب الأول أقرب ثلاثة مقاطع. الإجابة المتوقّعة عن النسخ الاحتياطي هي **كل سبت الساعة 03:40 بتوقيت باريس**، مع الاستشهاد بملف `sauvegarde.md`. يُفترض أن يمتنع المساعد عن الإجابة عن منطقة AWS. يتحقّق البرنامج من أن كل استشهاد يشير إلى مقطع موجود في نتائج الاسترجاع. اقرأ المقطع المشار إليه للتأكد من أنه يدعم الإجابة. [تضمينات Ollama](https://docs.ollama.com/api/embed)، [البحث في Qdrant](https://api.qdrant.tech/api-reference/search/query-points).

لإضافة مستنداتك، ضع ملفات Markdown أو TXT بترميز UTF-8 أو PDF بطبقة نصية في `corpus/`. إذا كان ملف PDF صورة ممسوحة ضوئيًا، فاستخرج النص محليًا باستخدام التعرّف الضوئي على الحروف (OCR). تأكّد من أن مستخدم الحاوية يستطيع قراءة الملفات المحدّدة. عند الضرورة استخدم مثلًا `chmod a+r corpus/runbook.pdf`، وحافظ على حصر الوصول إلى `~/lab-ai-ar` بحسابك على Ubuntu. أعد تنفيذ أمر `python rag.py` داخل الحاوية بعد كل إضافة أو حذف أو تغيير في تقسيم النص. تبقى المجموعات السابقة في قاعدة البيانات لإتاحة الرجوع إليها. راقب حجمها عند تكرار التجارب على مجموعة مستندات كبيرة.

## 5. التحقّق والنسخ الاحتياطي واستكشاف المشكلات

**اختبار التشغيل.** جرّب محادثة من هاتف متصل عبر 4G أو 5G، وجرّب طلب RAG يُرفق استشهادًا، ثم سؤالًا خارج نطاق المستندات. اختبر إعادة الاتصال بعد إعادة تشغيل مخطّط لها. تحقّق من تعذّر الوصول مباشرةً إلى المنافذ `3000` و`8001` و`11434` على عنوان Ubuntu من الشبكة المحلية. اعرض `sudo docker compose --profile rag ps` من Ubuntu للتأكد من ربطها بـ `127.0.0.1`.

**تقييم الإجابات.** من Ubuntu، شغّل مجموعة الأسئلة التجريبية المرفقة. يوضّح التقرير الإجابات وظهور المصدر ضمن أول ثلاث نتائج ووسيط زمن الاستجابة وقيمة تقريبية للمئين 95. تكون حالة الخروج 1 إذا فشل أحد الاختبارات. [التمارين ومعايير التقييم](FORMATION.md).

<div dir="ltr">

~~~bash
sudo docker compose --profile rag exec -T rag python eval_lab.py > resultats-4b.json
jq '.summary' resultats-4b.json
~~~

</div>

**النسخ الاحتياطي.** في Proxmox، جدوِل نسخ الآلة الافتراضية إلى وحدة تخزين أخرى، مثل جهاز NAS أو Proxmox Backup Server. تشمل نسخة الآلة بيانات Ollama وOpen WebUI وQdrant والمستندات وملف `.env` الذي يحفظ المفتاح السرّي. في حالة تثبيت Ubuntu مباشرةً، أوقف الحاويات بالأمر `sudo docker compose --profile rag stop` وانسخ المجلّد ووحدات تخزين Docker إلى وسيط آخر. اعرض موضع وحدة التخزين بالأمر `sudo docker volume inspect lab-ai-ar_webui_data`، وافحص أيضًا `lab-ai-ar_ollama_data` و`lab-ai-ar_qdrant_data`. استأنف الخدمات بالأمر `sudo docker compose --profile rag up -d`. اختبر الاستعادة في بيئة معزولة قبل إعادة توصيل نسخة الآلة الافتراضية بشبكتك الخاصة. [النسخ الاحتياطي في Proxmox](https://github.com/proxmox/pve-docs/blob/master/vzdump.adoc)، [نسخ وحدات تخزين Docker واستعادتها](https://docs.docker.com/engine/storage/volumes/#back-up-restore-or-migrate-data-volumes).

| المشكلة | ما ينبغي فحصه |
| --- | --- |
| تعذّر فتح المحادثة | نفّذ `curl -fsS http://127.0.0.1:3000/health` في Ubuntu، ثم افحص `tailscale status` و`tailscale serve status`. تأكّد من أن Tailscale يعمل على الحاسوب المحمول ومن صحة اسم الجهاز. |
| قائمة النماذج فارغة | افحص `sudo docker compose exec ollama ollama list` وإعداد **Connections → Ollama** في واجهة المحادثة. يجب أن يكون العنوان الداخلي `http://ollama:11434`. |
| تعذّر الوصول إلى RAG | افحص `/readyz` ونزّل `bge-m3` و`qwen3:4b` عند الحاجة. أعد الفهرسة إذا كان الاسم المستعار `runbooks` مفقودًا. راجع آخر السجلات عبر `sudo docker compose --profile rag logs --tail=60 rag qdrant ollama`. |
| بطء الاستدلال أو استخدام ذاكرة التبديل | افحص `free -h` و`sudo docker stats --no-stream` ونتيجة `ollama ps` داخل الحاوية. قارن زمن الطلب الأول بطلب بعد تحميل النموذج. استخدم 4B وقلّل طول السياق أو الإجابة عند الحاجة. |
| امتلاء مساحة القرص | افحص `df -h /` ومساحة التخزين في Proxmox و`sudo docker system df`. تحفظ وحدات التخزين النماذج والمحادثات والفهارس. استخدم `stop` للإيقاف و`up -d` للاستئناف. |

تستهدف إعدادات المختبر مستخدمًا واحدًا على المعالج المركزي. استخدم قياسات اليومين الأول والثاني لتحديد زمن الاستجابة المناسب وتقييم النموذج 8B قبل زيادة عدد المستخدمين.

</div>
