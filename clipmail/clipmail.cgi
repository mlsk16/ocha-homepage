#!/usr/local/bin/perl

#┌─────────────────────────────────
#│ CLIP-MAIL : clipmail.cgi - 2023/01/15
#│ copyright (c) kentweb, 1997-2023
#│ https://www.kent-web.com/
#└─────────────────────────────────

# モジュール実行
use strict;
use CGI::Carp qw(fatalsToBrowser);
use lib './lib';
use CGI::Minimal;

# 設定ファイル認識
require './lib/jacode.pl';
require './init.cgi';
my %cf = set_init();

# データ受理
CGI::Minimal::max_read_size($cf{maxdata});
my $cgi = CGI::Minimal->new;
error('容量オーバー') if ($cgi->truncated);
my ($key,$need,$in) = parse_form();

# 禁止ワードチェック
if ($cf{no_wd}) { check_word(); }

# ホスト取得＆チェック
my ($host,$addr) = get_host();

# 必須入力チェック
my ($check,@err);
if ($$in{need} || @$need > 0) {
	
	# needフィールドの値を必須配列に加える
	my @tmp = split(/\s+/,$$in{need});
	push(@$need,@tmp);
	
	# 必須配列の重複要素を排除
	my %count;
	@$need = grep {!$count{$_}++} @$need;
	
	# 必須項目の入力値をチェックする
	foreach (@$need) {
		
		# フィールドの値が投げられてこないもの（ラジオボタン等）
		if (!defined($$in{$_})) {
			$check++;
			push(@$key,$_);
			push(@err,$_);
		
		# 入力なしの場合
		} elsif ($$in{$_} eq "") {
			$check++;
			push(@err,$_);
		}
	}
}

# 入力内容マッチ
my ($match1,$match2);
if ($$in{match}) {
	($match1,$match2) = split(/\s+/,$$in{match},2);
	
	if ($$in{$match1} ne $$in{$match2}) {
		error("$match1と$match2の再入力内容が異なります");
	}
}

# 入力チェック確認画面
if ($check) { err_input($match2); }

# --- プレビュー
if ($$in{mode} ne "send") {
	# 確認画面
	prev_form();

# --- 送信実行
} else {
	# sendmail送信
	send_mail();
}

#-----------------------------------------------------------
#  プレビュー
#-----------------------------------------------------------
sub prev_form {
	# 送信内容チェック
	error("データを取得できません") if (@$key == 0);
	
	# メール書式チェック
	check_email($$in{email}) if ($$in{email});
	
	# 時間取得
	my $time = time;
	
	# 許可拡張子をハッシュ化
	my %ex;
	for ( split(/,/,$cf{extension}) ) { $ex{$_}++; }
	
	# 順番
	if ($$in{sort}) {
		my (@tmp,%tmp);
		for ( split(/\s+/,$$in{sort}) ) {
			push(@tmp,$_);
			$tmp{$_}++;
		}
		for (@$key) {
			if (!defined $tmp{$_}) { push(@tmp,$_); }
		}
		@$key = @tmp;
	}
	
	# 添付確認
	my ($err,@ext,%file,%ext);
	foreach (@$key) {
		if (/^clip-(\d+)$/) {
			my $num = $1;
			
			# ファイル名取得
			my $fname = $cgi->param_filename("clip-$num");
			$fname =~ s/[\r\n]//g;
			
			if ($fname =~ /([^\\\/:]+)\.([^\\\/:\.]+)$/) {
				# ファイル名定義
				$file{$num} = hex_encode("$1.$2");
				
				# 拡張子チェック
				$ext{$num} = $2;
				$ext{$num} =~ tr/A-Z/a-z/;
				if (!defined($ex{$ext{$num}}) && $cf{extension}) {
					$err .= "$ext{$num},";
				}
				# 添付ファイル番号を覚えておく
				push(@ext,$num);
			}
		}
	}
	# 拡張子エラー
	if ($err) {
		$err =~ s/,$//;
		error("添付ファイルで許可されない拡張子があります → $err");
	}
	
	# 添付あり
	if (@ext > 0) {
		# 一時ディレクトリを掃除
		clean_dir();
		
		# アップロード実行
		foreach my $i (@ext) {
			# ファイル定義
			my $upfile = "$cf{upldir}/$time-$i.$ext{$i}";
			
			# ファイルアップロード
			my $buf;
			open(UP,"+> $upfile") or error("up err: $upfile");
			binmode(UP);
			print UP $$in{"clip-$i"};
			close(UP);
		}
	}
	
	# セッション生成
	my $ses = make_ses();
	
	# テンプレート読込
	open(IN,"$cf{tmpldir}/conf.html") or error("open err: conf.html");
	my $tmpl = join('',<IN>);
	close(IN);
	
	# 置き換え
	$tmpl =~ s/!(mail_cgi|cmnurl)!/$cf{$1}/g;
	
	# テンプレート分割
	my ($head,$loop,$foot) = $tmpl =~ m|(.+)<!-- cell -->(.+?)<!-- /cell -->(.+)|s
			? ($1,$2,$3)
			: error("テンプレートが不正です");
	
	# 引数
	my $hidden;
	$hidden .= qq|<input type="hidden" name="mode" value="send">\n|;
	$hidden .= qq|<input type="hidden" name="ses_id" value="$ses">\n|;
	$hidden .= qq|<input type="hidden" name="sort" value="$$in{sort}">\n|;
	
	# 項目
	my ($bef,$item);
	foreach my $key (@$key) {
		next if ($bef eq $key);
		
		# 画像SUBMITボタンは無視
		next if ($key eq "x");
		next if ($key eq "y");
		next if ($key eq "need");
		next if ($key eq "match");
		next if ($key eq "sort");
		next if ($$in{match} && $key eq $match2);
		if ($key eq 'subject') {
			$hidden .= qq|<input type="hidden" name="$key" value="$$in{subject}">\n|;
			next;
		}
		
		# 添付のとき
		if ($key =~ /^clip-(\d+)$/i) {
			my $no = $1;
			if (defined($file{$no})) {
				$hidden .= qq|<input type="hidden" name="$key" value="$file{$no}:$time-$no.$ext{$no}">\n|;
			} else {
				$hidden .= qq|<input type="hidden" name="$key" value="">\n|;
			}
			
			my $tmp = $loop;
			$tmp =~ s/!key!/添付$no/;
			
			# 画像のとき
			if ($ext{$no} =~ /^(gif|jpe?g|png|bmp)$/i && -B "$cf{upldir}/$time-$no.$ext{$no}") {
				
				# 表示サイズ調整
				my ($w,$h) = resize("$cf{upldir}/$time-$no.$ext{$no}", $1);
				$tmp =~ s|!val!|<img src="$cf{uplurl}/$time-$no.$ext{$no}" width="$w" height="$h" alt="">|;
				
			# 画像以外
			} else {
				$tmp =~ s/!val!/hex_decode($file{$no})/e;
			}
			$item .= $tmp;
		
		# テキスト（添付以外）
		} else {
			check_key($key) if ($cf{check_key});
			my $val = hex_encode($$in{$key});
			$hidden .= qq|<input type="hidden" name="$key" value="$val">\n|;
			
			# 改行変換
			$$in{$key} =~ s|\t|<br>|g;
			
			my $tmp = $loop;
			if (defined($cf{replace}->{$key})) {
				$tmp =~ s/!key!/$cf{replace}->{$key}/;
			} else {
				$tmp =~ s/!key!/$key/;
			}
			$tmp =~ s/!val!/$$in{$key}/;
			$item .= $tmp;
		}
		$bef = $key;
	}
	
	# 文字置換
	for ($head,$foot) {
		s/!mail_cgi!/$cf{mail_cgi}/g;
		s/<!-- hidden -->/$hidden/g;
	}
	
	# 画面展開
	print "Content-type: text/html; charset=utf-8\n\n";
	print $head,$item;
	
	# フッタ
	footer($foot);
}

#-----------------------------------------------------------
#  送信実行
#-----------------------------------------------------------
sub send_mail {
	# 送信内容チェック
	error("データを取得できません") if (@$key == 0);
	
	# セッションチェック
	check_ses();
	
	# メール書式チェック
	check_email($$in{email},'send') if ($$in{email});
	
	# 時間取得
	my ($date1,$date2) = get_time();
	
	# ブラウザ情報
	my $agent = $ENV{HTTP_USER_AGENT};
	$agent =~ s/[<>&"'()+;]//g;
	
	# 順番
	if ($$in{sort}) {
		my (@tmp,%tmp);
		for ( split(/\s+/,$$in{sort}) ) {
			push(@tmp,$_);
			$tmp{$_}++;
		}
		for (@$key) {
			if (!defined $tmp{$_}) { push(@tmp,$_); }
		}
		@$key = @tmp;
	}
	
	# 本文テンプレ読み込み
	open(IN,"$cf{tmpldir}/mail.txt") or error("open err: mail.txt");
	my $mail = join('',<IN>);
	close(IN);
	
	# テンプレ変数変換
	$mail =~ s/!date!/$date1/g;
	$mail =~ s/!agent!/$agent/g;
	$mail =~ s/!host!/$host/g;
	
	# 自動返信ありのとき
	my $reply;
	if ($cf{auto_res}) {
		# テンプレ
		open(IN,"$cf{tmpldir}/reply.txt") or error("open err: reply.txt");
		$reply = join('',<IN>);
		close(IN);
		
		# 変数変換
		$reply =~ s/!date!/$date1/g;
	}
	
	# ログファイルオープン
	open(DAT,"+< $cf{datadir}/log.cgi") or error("open err: log.cgi");
	eval "flock(DAT,2);";
	
	# 先頭行を分解
	my $top_log = <DAT>;
	jcode::convert(\$top_log,'utf8','sjis');
	my ($log_date,$log_ip,$log_data) = split(/<>/,$top_log,3);
	
	# ハッシュ%logに各項目を代入
	my %log;
	foreach ( split(/<>/,$log_data) ) {
		my ($key,$val) = split(/=/,$_,2);
		$log{$key} = $val;
	}
	
	# 本文のキーを展開
	my ($bef,$mbody,$log,$flg,@ext);
	foreach (@$key) {
		# 本文に含めない部分を排除
		next if ($_ eq "mode");
		next if ($_ eq "need");
		next if ($_ eq "match");
		next if ($_ eq "sort");
		next if ($_ eq "ses_id");
		next if ($_ eq "subject");
		next if ($$in{match} && $_ eq $match2);
		next if ($bef eq $_);
		
		# 添付
		my $upl;
		if (/^clip-(\d+)$/i) {
			my $no = $1;
			if ($$in{"clip-$no"}) { push(@ext,$no); }
			
			# ファイル名hexデコード
			my ($uplfile,$tmpfile) = split(/:/,$$in{"clip-$no"});
			$uplfile = hex_decode($uplfile);
			$$in{"clip-$no"} = "$uplfile:$tmpfile";
			
			# ログ蓄積
			$log .= "$_=$uplfile<>";
			my $tmp = "添付$no = $uplfile\n";
			$mbody .= $tmp;
			
			# 内容を二重送信チェック
			if ($uplfile ne $log{$_}) { $flg++; }
			next;
		}
		
		# hexデコード
		$$in{$_} = hex_decode($$in{$_});
		
		# name値の名前置換
		my $key_name = defined($cf{replace}->{$_}) ? $cf{replace}->{$_} : $_;
		
		# 内容を二重送信チェック
		if ($$in{$_} ne $log{$key_name}) { $flg++; }
		
		# エスケープ
		$$in{$_} =~ s/\.\n/\. \n/g;
		
		# 添付ファイル風の文字列拒否
		$$in{$_} =~ s/Content-Disposition:\s*attachment;.*//ig;
		$$in{$_} =~ s/Content-Transfer-Encoding:.*//ig;
		$$in{$_} =~ s/Content-Type:\s*multipart\/mixed;\s*boundary=.*//ig;
		
		# ログ蓄積
		$log .= "$key_name=$$in{$_}<>";
		
		# 改行復元
		$$in{$_} =~ s/\t/\n/g;
		
		# HTMLタグ復元
		$$in{$_} =~ s/&lt;/</g;
		$$in{$_} =~ s/&gt;/>/g;
		$$in{$_} =~ s/&quot;/"/g;
		$$in{$_} =~ s/&#39;/'/g;
		$$in{$_} =~ s/&amp;/&/g;
		
		# 本文内容
		my $tmp;
		if ($$in{$_} =~ /\n/) {
			$tmp = "$key_name = \n$$in{$_}\n";
		} else {
			$tmp = "$key_name = $$in{$_}\n";
		}
		$mbody .= $tmp;
		
		$bef = $_;
	}
	
	if (!$flg) {
		close(DAT);
		error("二重送信のため処理を中止しました");
	}
	# ログコード変換
	jcode::convert(\$log,'sjis','utf8');
	
	# ログ保存
	my @log;
	if ($cf{keep_log} > 0) {
		my $i = 0;
		seek(DAT, 0, 0);
		while(<DAT>) {
			push(@log,$_);
			
			$i++;
			last if ($i >= $cf{keep_log} - 1);
		}
	}
	seek(DAT,0,0);
	print DAT "date=$date1<>ip=$addr<>$log\n";
	print DAT @log if (@log > 0);
	truncate(DAT,tell(DAT));
	close(DAT);
	
	# 本文テンプレ内の変数を置き換え
	$mail =~ s/!message!/$mbody/;
	
	# 返信テンプレ内の変数を置き換え
	$reply =~ s/!message!/$mbody/ if ($cf{auto_res});
	
	# コード変換
	require './lib/base64.pl';
	if ($cf{send_b64} == 1) {
		$mail  = conv_b64($mail);
		$reply = conv_b64($reply) if ($cf{auto_res});
	
	} else {
		my $tmp;
		for my $ml ( split(/\n/,$mail) ) {
			jcode::convert(\$ml,'jis','utf8');
			$tmp .= "$ml\n";
		}
		$mail = $tmp;
		
		if ($cf{auto_res}) {
			my $tmp;
			for my $ml ( split(/\n/,$reply) ) {
				jcode::convert(\$ml,'jis','utf8');
				$tmp .= "$ml\n";
			}
			$reply = $tmp;
		}
	}
	
	# メールアドレスがない場合は送信先に置き換え
	my $email = $$in{email} eq '' ? $cf{mailto} : $$in{email};
	
	# MIMEエンコード
	my $sub_me = $$in{subject} ne '' && defined($cf{multi_sub}->{$$in{subject}}) ? $cf{multi_sub}->{$$in{subject}} : $cf{subject};
	$sub_me = mime_unstructured_header($sub_me);
	my $from;
	if ($$in{name}) {
		$$in{name} =~ s/[\r\n]//g;
		$from = mime_unstructured_header("\"$$in{name}\" <$email>");
	} else {
		$from = $email;
	}
	
	# 区切り線
	my $cut = "------_" . time . "_MULTIPART_MIXED_";
	
	# --- 送信内容フォーマット開始
	# ヘッダー
	my $body;
	$body .= "To: $cf{mailto}\n";
	$body .= "From: $from\n";
	$body .= "Subject: $sub_me\n";
	$body .= "MIME-Version: 1.0\n";
	$body .= "Date: $date2\n";
	
	# 添付ありのとき
	if (@ext > 0) {
		$body .= "Content-Type: multipart/mixed; boundary=\"$cut\"\n";
	} else {
		if ($cf{send_b64} == 1) {
			$body .= "Content-type: text/plain; charset=utf-8\n";
			$body .= "Content-Transfer-Encoding: base64\n";
		} else {
			$body .= "Content-type: text/plain; charset=iso-2022-jp\n";
			$body .= "Content-Transfer-Encoding: 7bit\n";
		}
	}
	
	$body .= "X-Mailer: $cf{version}\n\n";
	
	# 本文
	if (@ext > 0) {
		$body .= "--$cut\n";
		if ($cf{send_b64} == 1) {
			$body .= "Content-type: text/plain; charset=utf-8\n";
			$body .= "Content-Transfer-Encoding: base64\n\n";
		} else {
			$body .= "Content-type: text/plain; charset=iso-2022-jp\n";
			$body .= "Content-Transfer-Encoding: 7bit\n\n";
		}
	}
	$body .= "$mail\n";
	
	# 返信内容フォーマット
	my $res_body;
	if ($cf{auto_res}) {
		# 件名MIMEエンコード
		my $re_sub = mime_unstructured_header($cf{sub_reply});
		
		$res_body .= "To: $email\n";
		$res_body .= "From: $cf{mailto}\n";
		$res_body .= "Subject: $re_sub\n";
		$res_body .= "MIME-Version: 1.0\n";
		$res_body .= "Date: $date2\n";
		
		if ($cf{send_b64} == 1) {
			$res_body .= "Content-type: text/plain; charset=utf-8\n";
			$res_body .= "Content-Transfer-Encoding: base64\n";
		} else {
			$res_body .= "Content-type: text/plain; charset=iso-2022-jp\n";
			$res_body .= "Content-Transfer-Encoding: 7bit\n";
		}
		
		$res_body .= "X-Mailer: $cf{version}\n\n";
		$res_body .= "$reply\n";
	}
	
	# 添付あり
	if (@ext > 0) {
		# 添付展開
		foreach my $i (@ext) {
			# ファイル名と一時ファイル名に分割
			my ($fname,$tmpfile) = split(/:/,$$in{"clip-$i"},2);
			
			# ファイル名汚染チェック
			next if ($tmpfile !~ /^\d+\-$i\.\w+$/);
			
			# 一時ファイル名が存在しないときはスキップ
			next if (! -f "$cf{upldir}/$tmpfile");
			
			$fname = mime_unstructured_header($fname);
			
			# 添付ファイルを定義
			$body .= qq|--$cut\n|;
			$body .= qq|Content-Type: application/octet-stream; name="$fname"\n|;
			$body .= qq|Content-Disposition: attachment; filename="$fname"\n|;
			$body .= qq|Content-Transfer-Encoding: Base64\n\n|;
			
			# 一時ファイルをBase64変換
			my $buf;
			open(IN,"$cf{upldir}/$tmpfile");
			binmode(IN);
			while ( read(IN,$buf,60*57) ) {
				$body .= base64::b64encode($buf);
			}
			close(IN);
			
			# 一時ファイル削除
			unlink("$cf{upldir}/$tmpfile");
		}
		$body .= "--$cut--\n";
	}
	
	# senmdailコマンド
	my $scmd = $cf{send_fcmd} ? "$cf{sendmail} -t -i -f $email" : "$cf{sendmail} -t -i";
	
	# 本文送信
	open(MAIL,"| $scmd") or error("メール送信失敗");
	print MAIL "$body\n";
	close(MAIL);
	
	# 返信送信
	if ($cf{auto_res}) {
		my $scmd = $cf{send_fcmd} ? "$cf{sendmail} -t -i -f $cf{mailto}" : "$cf{sendmail} -t -i";
		
		open(MAIL,"| $scmd") or error("メール送信失敗");
		print MAIL "$res_body\n";
		close(MAIL);
	}
	
	# リロード
	if ($cf{reload}) {
		if ($ENV{PERLXS} eq "PerlIS") {
			print "HTTP/1.0 302 Temporary Redirection\r\n";
			print "Content-type: text/html\n";
		}
		print "Location: $cf{back}\n\n";
		exit;
	
	# 完了メッセージ
	} else {
		open(IN,"$cf{tmpldir}/thanks.html") or error("open err: thanks.html");
		my $tmpl = join('',<IN>);
		close(IN);
		
		$tmpl =~ s/!(back|cmnurl)!/$cf{$1}/g;
		
		# 表示
		print "Content-type: text/html; charset=utf-8\n\n";
		footer($tmpl);
	}
}

#-----------------------------------------------------------
#  入力エラー表示
#-----------------------------------------------------------
sub err_input {
	my $match2 = shift;
	
	# 順番
	if ($$in{sort}) {
		my (@tmp,%tmp);
		for ( split(/\s+/,$$in{sort}) ) {
			push(@tmp,$_);
			$tmp{$_}++;
		}
		for (@$key) {
			if (!defined($tmp{$_})) { push(@tmp,$_); }
		}
		@$key = @tmp;
	}
	
	# テンプレート読み込み
	open(IN,"$cf{tmpldir}/error.html") or die;
	my $tmpl = join('',<IN>);
	close(IN);
	
	$tmpl =~ s/!cmnurl!/$cf{cmnurl}/g;
	
	# テンプレート分割
	my ($head,$loop,$foot) = $tmpl =~ m|(.+)<!-- cell -->(.+?)<!-- /cell -->(.+)|s
			? ($1,$2,$3)
			: error("テンプレート不正");
	
	# 画面展開
	print "Content-type: text/html; charset=utf-8\n\n";
	print $head;
	
	# 内容展開
	my $bef;
	foreach my $key (@$key) {
		next if ($key eq "need");
		next if ($key eq "match");
		next if ($key eq "sort");
		next if ($$in{match} && $key eq $match2);
		next if ($bef eq $key);
		next if ($key eq "x");
		next if ($key eq "y");
		next if ($key eq "subject");
		
		my $key_name = $key;
		my $tmp = $loop;
		if ($key =~ /^clip-(\d+)$/i) {
			$key_name = "添付$1";
			
			# 添付時はファイル名
			my $fname = $cgi->param_filename("clip-$1");
			if ($fname =~ /([^\\\/:]+)\.([^\\\/:\.]+)$/) { $$in{$key} = "$1.$2"; }
			
		} elsif(defined($cf{replace}->{$key})) {
			$key_name = $cf{replace}->{$key};
		}
		$tmp =~ s/!key!/$key_name/;
		
		my $erflg;
		foreach my $err (@err) {
			if ($err eq $key) {
				$erflg++;
				last;
			}
		}
		# 入力なし：エラー表示
		if ($erflg) {
			$tmp =~ s/!val!/<span class="msg">$key_nameは入力必須です.<\/span>/;
		
		# 正常時
		} else {
			# 添付以外のとき改行復元
			if ($key !~ /^clip-\d+$/i) { $$in{$key} =~ s|\t|<br>|g; }
			$tmp =~ s/!val!/$$in{$key}/;
		}
		print $tmp;
		
		$bef = $key;
	}
	
	# フッタ
	print $foot;
	exit;
}

#-----------------------------------------------------------
#  フォームデコード
#-----------------------------------------------------------
sub parse_form {
	my ($clip,@key,@need,%in);
	foreach my $key ( $cgi->param() ) {
		my $val;
		
		# 添付
		if ($key =~ /^clip-\d+$/) {
			$val = $cgi->param($key);
			if ($val) { $clip++; }
		
		# テキスト系
		} else {
			
			# 複数値の場合はスペースで区切る
			$val = join(" ", $cgi->param($key));
			
			# 無害化/改行変換
			$key =~ s/[<>&"'\r\n]//g;
			$val =~ s/&/&amp;/g;
			$val =~ s/</&lt;/g;
			$val =~ s/>/&gt;/g;
			$val =~ s/"/&quot;/g;
			$val =~ s/'/&#39;/g;
			$val =~ s/\r\n/\t/g;
			$val =~ s/\r/\t/g;
			$val =~ s/\n/\t/g;
			
			# 入力必須
			if ($key =~ /^_(.+)/) {
				$key = $1;
				push(@need,$key);
			}
		}
		
		# 受け取るキーの順番を覚えておく
		push(@key,$key);
		
		# %inハッシュに代入
		$in{$key} = $val;
	}
	
	# post送信チェック
	if ($cf{postonly} && $ENV{REQUEST_METHOD} ne 'POST') {
		error("不正なアクセスです");
	}
	# 添付拒否の場合
	if (!$cf{attach} && $clip) {
		error("不正なアクセスです");
	}
	
	# リファレンスで返す
	return (\@key,\@need,\%in);
}

#-----------------------------------------------------------
#  フッター
#-----------------------------------------------------------
sub footer {
	my $foot = shift;
	
	# 著作権表記（削除・改変禁止）
	my $copy = <<EOM;
<p style="margin-top:2em;text-align:center;font-family:Verdana,Helvetica,Arial;font-size:10px;">
	- <a href="https://www.kent-web.com/" target="_top">CLIP MAIL</a> -
</p>
EOM

	if ($foot =~ /(.+)(<\/body[^>]*>.*)/si) {
		print "$1$copy$2\n";
	} else {
		print "$foot$copy\n";
		print "</body></html>\n";
	}
	exit;
}

#-----------------------------------------------------------
#  エラー処理
#-----------------------------------------------------------
sub error {
	my $err = shift;
	
	open(IN,"$cf{tmpldir}/error.html") or die;
	my $tmpl = join('', <IN>);
	close(IN);
	
	# 文字置き換え
	$tmpl =~ s/!key!/エラー内容/g;
	$tmpl =~ s|!val!|<span class="msg">$err</span>|g;
	$tmpl =~ s/!cmnurl!/$cf{cmnurl}/g;
	
	print "Content-type: text/html; charset=utf-8\n\n";
	print $tmpl;
	exit;
}

#-----------------------------------------------------------
#  時間取得
#-----------------------------------------------------------
sub get_time {
	$ENV{TZ} = "JST-9";
	my ($sec,$min,$hour,$mday,$mon,$year,$wday) = localtime(time);
	my @week  = qw|Sun Mon Tue Wed Thu Fri Sat|;
	my @month = qw|Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec|;
	
	# 日時のフォーマット
	my $date1 = sprintf("%04d/%02d/%02d(%s) %02d:%02d:%02d",
			$year+1900,$mon+1,$mday,$week[$wday],$hour,$min,$sec);
	my $date2 = sprintf("%s, %02d %s %04d %02d:%02d:%02d",
			$week[$wday],$mday,$month[$mon],$year+1900,$hour,$min,$sec) . " +0900";
	
	return ($date1,$date2);
}

#-----------------------------------------------------------
#  ホスト名取得
#-----------------------------------------------------------
sub get_host {
	# ホスト名取得
	my $host = $ENV{REMOTE_HOST};
	my $addr = $ENV{REMOTE_ADDR};
	
	if ($cf{gethostbyaddr} && ($host eq "" || $host eq $addr)) {
		$host = gethostbyaddr(pack("C4", split(/\./, $addr)), 2);
	}
	$host ||= $addr;
	
	# チェック
	if ($cf{denyhost}) {
		my $flg;
		foreach ( split(/\s+/, $cf{denyhost}) ) {
			s/\./\\\./g;
			s/\*/\.\*/g;
			
			if ($host =~ /$_/i) { $flg++; last; }
		}
		if ($flg) { error("アクセスを許可されていません"); }
	}
	
	return ($host,$addr);
}

#-----------------------------------------------------------
#  セッション生成
#-----------------------------------------------------------
sub make_ses {
	# 時間取得
	my $now = time;
	
	# セッション発行
	my @wd = (0 .. 9, 'a' .. 'z', 'A' .. 'Z', '_');
	my $ses;
	srand;
	for (1 .. 25) { $ses .= $wd[int(rand(@wd))]; }
	
	# セッション情報をセット
	my @log;
	open(DAT,"+< $cf{datadir}/ses.cgi") or error("open err: ses.cgi");
	eval 'flock(DAT,2);';
	while(<DAT>) {
		chomp;
		my ($id,$time) = split(/\t/);
		next if ($now - $time > $cf{sestime} * 60);
		
		push(@log,"$_\n");
	}
	unshift(@log,"$ses\t$now\n");
	seek(DAT,0,0);
	print DAT @log;
	truncate(DAT,tell(DAT));
	close(DAT);
	
	return $ses;
}

#-----------------------------------------------------------
#  セッションチェック
#-----------------------------------------------------------
sub check_ses {
	# 整合性チェック
	if ($$in{ses_id} !~ /^\w{25}$/) { error('不正なアクセスです'); }
	
	my $now = time;
	my $flg;
	open(DAT,"$cf{datadir}/ses.cgi") or error("open err: ses.cgi");
	while(<DAT>) {
		chomp;
		my ($id,$time) = split(/\t/);
		next if ($now - $time > $cf{sestime} * 60);
		
		if ($id eq $$in{ses_id}) {
			$flg++;
			last;
		}
	}
	close(DAT);
	
	# エラーのとき
	if (!$flg) {
		error('確認画面表示後一定時間が経過しました。最初からやり直してください');
	}
}

#-----------------------------------------------------------
#  hexエンコード
#-----------------------------------------------------------
sub hex_encode {
	my $str = shift;
	
	$str =~ s/(.)/unpack('H2', $1)/eg;
	$str =~ s/\n/\t/g;
	return $str;
}

#-----------------------------------------------------------
#  hexデコード
#-----------------------------------------------------------
sub hex_decode {
	my $str = shift;
	
	$str =~ s/\t/\n/g;
	$str =~ s/([0-9A-Fa-f]{2})/pack('H2', $1)/eg;
	return $str;
}

#-----------------------------------------------------------
#  電子メール書式チェック
#-----------------------------------------------------------
sub check_email {
	my ($eml,$job) = @_;
	
	# 送信時はhexデコード
	if ($job eq 'send') { $eml = hex_decode($eml); }
	
	# E-mail書式チェック
	if ($eml =~ /\,/) {
		error("メールアドレスにコンマ ( , ) が含まれています");
	}
	if ($eml ne '' && $eml !~ /^[\w\.\-]+\@[\w\.\-]+\.[a-zA-Z]{2,6}$/) {
		error("メールアドレスの書式が不正です");
	}
}

#-----------------------------------------------------------
#  name値チェック
#-----------------------------------------------------------
sub check_key {
	my $key = shift;
	
	if ($key !~ /^(?:[0-9a-zA-Z_-]|[\xE0-\xEF][\x80-\xBF]{2})+$/) {
		error("name値に不正な文字が含まれています");
	}
}

#-----------------------------------------------------------
#  禁止ワードチェック
#-----------------------------------------------------------
sub check_word {
	my $flg;
	foreach (@$key) {
		foreach my $wd ( split(/,/, $cf{no_wd}) ) {
			if (index($$in{$_},$wd) >= 0) {
				$flg++;
				last;
			}
		}
		if ($flg) { error("禁止ワードが含まれています"); }
	}
}

#-----------------------------------------------------------
#  mimeエンコード
#  [quote] http://www.din.or.jp/~ohzaki/perl.htm#JP_Base64
#-----------------------------------------------------------
sub mime_unstructured_header {
  my $oldheader = shift;
  jcode::convert(\$oldheader,'euc','utf8');
  my ($header,@words,@wordstmp,$i);
  my $crlf = $oldheader =~ /\n$/;
  $oldheader =~ s/\s+$//;
  @wordstmp = split /\s+/, $oldheader;
  for ($i = 0; $i < $#wordstmp; $i++) {
    if ($wordstmp[$i] !~ /^[\x21-\x7E]+$/ and
	$wordstmp[$i + 1] !~ /^[\x21-\x7E]+$/) {
      $wordstmp[$i + 1] = "$wordstmp[$i] $wordstmp[$i + 1]";
    } else {
      push(@words, $wordstmp[$i]);
    }
  }
  push(@words, $wordstmp[-1]);
  foreach my $word (@words) {
    if ($word =~ /^[\x21-\x7E]+$/) {
      $header =~ /(?:.*\n)*(.*)/;
      if (length($1) + length($word) > 76) {
	$header .= "\n $word";
      } else {
	$header .= $word;
      }
    } else {
      $header = add_encoded_word($word, $header);
    }
    $header =~ /(?:.*\n)*(.*)/;
    if (length($1) == 76) {
      $header .= "\n ";
    } else {
      $header .= ' ';
    }
  }
  $header =~ s/\n? $//mg;
  $crlf ? "$header\n" : $header;
}
sub add_encoded_word {
  my ($str, $line) = @_;
  my $result;
  my $ascii = '[\x00-\x7F]';
  my $twoBytes = '[\x8E\xA1-\xFE][\xA1-\xFE]';
  my $threeBytes = '\x8F[\xA1-\xFE][\xA1-\xFE]';
  while (length($str)) {
    my $target = $str;
    $str = '';
    if (length($line) + 22 +
	($target =~ /^(?:$twoBytes|$threeBytes)/o) * 8 > 76) {
      $line =~ s/[ \t\n\r]*$/\n/;
      $result .= $line;
      $line = ' ';
    }
    while (1) {
      my $encoded = '=?ISO-2022-JP?B?' .
      b64encode(jcode::jis($target, 'euc', 'z')) . '?=';
      if (length($encoded) + length($line) > 76) {
	    $target =~ s/($threeBytes|$twoBytes|$ascii)$//o;
	    $str = $1 . $str;
      } else {
	    $line .= $encoded;
	    last;
      }
    }
  }
  $result . $line;
}
# [quote] http://www.tohoho-web.com/perl/encode.htm
sub b64encode {
    my $buf = shift;
    my ($mode,$tmp,$ret);
    my $b64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                . "abcdefghijklmnopqrstuvwxyz"
                . "0123456789+/";
	
    $mode = length($buf) % 3;
    if ($mode == 1) { $buf .= "\0\0"; }
    if ($mode == 2) { $buf .= "\0"; }
    $buf =~ s/(...)/{
        $tmp = unpack("B*", $1);
        $tmp =~ s|(......)|substr($b64, ord(pack("B*", "00$1")), 1)|eg;
        $ret .= $tmp;
    }/eg;
    if ($mode == 1) { $ret =~ s/..$/==/; }
    if ($mode == 2) { $ret =~ s/.$/=/; }
    
    return $ret;
}

#-----------------------------------------------------------
#  Base64エンコード
#-----------------------------------------------------------
sub conv_b64 {
	my $str = shift;
	
	$str =~ s/\n/\r\n/g;
	return base64::b64encode($str);
}

#-----------------------------------------------------------
#  一時ディレクトリ掃除
#-----------------------------------------------------------
sub clean_dir {
	# ディレクトリ内読み取り
	opendir(DIR,"$cf{upldir}");
	my @dir = readdir(DIR);
	closedir(DIR);
	
	for (@dir) {
		# 対象外はスキップ
		next if ($_ eq '.');
		next if ($_ eq '..');
		next if ($_ eq 'index.html');
		next if ($_ eq '.htaccess');
		
		# ファイル時間取得
		my $mtime = (stat("$cf{upldir}/$_"))[9];
		
		# 1時間以上経過しているファイルは削除
		if (time - $mtime > 3600) { unlink("$cf{upldir}/$_"); }
	}
}

#-----------------------------------------------------------
#  画像リサイズ
#-----------------------------------------------------------
sub resize {
	my ($path,$ext) = @_;
	
	# サイズ取得
	my ($w,$h);
	if ($ext =~ /^gif$/i) {
		($w,$h) = g_size($path);
	
	} elsif ($ext =~ /^jpe?g$/i) {
		($w,$h) = j_size($path);
	
	} elsif ($ext =~ /^png$/i) {
		($w,$h) = p_size($path);
	
	} elsif ($ext =~ /^bmp$/i) {
		($w,$h) = b_size($path);
	}
	
	# 調整
	if ($w > $cf{img_max_w} || $h > $cf{img_max_h}) {
		my $w2 = $cf{img_max_w} / $w;
		my $h2 = $cf{img_max_h} / $h;
		my $key;
		if ($w2 < $h2) {
			$key = $w2;
		} else {
			$key = $h2;
		}
		$w = int ($w * $key) || 1;
		$h = int ($h * $key) || 1;
	}
	($w,$h);
}

#-----------------------------------------------------------
#  JPEGサイズ認識
#-----------------------------------------------------------
sub j_size {
	my $image = shift;
	
	my ($w,$h,$t);
	open(IMG, "$image") or return (0,0);
	binmode(IMG);
	read(IMG, $t, 2);
	while (1) {
		read(IMG, $t, 4);
		my ($m, $c, $l) = unpack("a a n", $t);
		
		if ($m ne "\xFF") {
			$w = $h = 0;
			last;
		} elsif ((ord($c) >= 0xC0) && (ord($c) <= 0xC3)) {
			read(IMG, $t, 5);
			($h, $w) = unpack("xnn", $t);
			last;
		} else {
			read(IMG, $t, ($l - 2));
		}
	}
	close(IMG);
	
	($w,$h);
}

#-----------------------------------------------------------
#  GIFサイズ認識
#-----------------------------------------------------------
sub g_size {
	my $image = shift;
	
	my $data;
	open(IMG,"$image") or return (0,0);
	binmode(IMG);
	sysread(IMG, $data, 10);
	close(IMG);
	
	if ($data =~ /^GIF/) { $data = substr($data, -4); }
	my $w = unpack("v", substr($data, 0, 2));
	my $h = unpack("v", substr($data, 2, 2));
	
	($w,$h);
}

#-----------------------------------------------------------
#  PNGサイズ認識
#-----------------------------------------------------------
sub p_size {
	my $image = shift;
	
	my $data;
	open(IMG, "$image") or return (0,0);
	binmode(IMG);
	read(IMG, $data, 24);
	close(IMG);
	
	my $w = unpack("N", substr($data, 16, 20));
	my $h = unpack("N", substr($data, 20, 24));
	
	($w,$h);
}

#-----------------------------------------------------------
#  BMPサイズ
#-----------------------------------------------------------
sub b_size {
	my $image = shift;
	
	my $data;
	open(IMG, "$image") or return (0,0);
	binmode(IMG);
	seek(IMG, 0, 0);
	read(IMG, $data, 6);
	seek(IMG, 12, 1);
	read(IMG, $data, 8);
	
	unpack("VV", $data);
}

