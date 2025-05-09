#┌─────────────────────────────────
#│ ログインモジュール v1.5
#│ login.pl - 2022/01/30
#│ copyright (c) kentweb, 1997-2022
#│ https://www.kent-web.com/
#└─────────────────────────────────
# [ 必要ファイル構成 ]
#  lib/CGI/Session.pm
#  lib/CGI/Session/*.*
#  lib/Digest/SHA/PurePerl.pm
#  data/pass.dat
#  data/pwd/
#  data/ses/

#-----------------------------------------------------------
#  アクセス認証
#-----------------------------------------------------------
sub auth_login {
	$in{id} =~ s/\W//g;
	$in{pw} =~ s/\W//g;
	
	# ログイン
	if ($in{login} && $in{id} ne '' && $in{pw} ne '') {
		
		if (-e "$cf{datadir}/pwd/$in{id}.lock") {
			
			my $mtime = (stat("$cf{datadir}/pwd/$in{id}.lock"))[9];
			
			# 自動解除
			if ($cf{lock_days} > 0 && (time - $mtime > $cf{lock_days} * 3600)) {
				unlink("$cf{datadir}/pwd/$in{id}.lock");
			
			# ログインを全ブロック
			} else {
				auth_err("このログインIDは現在使用できません");
			}
		}
		
		my ($flg,$crypt);
		open(IN,"$cf{datadir}/pass.dat") or auth_err("open err: pass.dat");
		while(<IN>) {
			chomp;
			my ($id,$pw) = split(/\t/);
			
			if ($in{id} eq $id) {
				$flg++;
				$crypt = $pw;
				last;
			}
		}
		close(IN);
		
		if (!$flg) { auth_err("認証できません"); }
		elsif (!decrypt($crypt,$in{pw})) {
			
			if (!-e "$cf{datadir}/pwd/$in{id}.dat") {
				open(DAT,"> $cf{datadir}/pwd/$in{id}.dat");
				close(DAT);
			}
			open(DAT,"+< $cf{datadir}/pwd/$in{id}.dat");
			eval "flock(DAT,2);";
			my $kai = <DAT> + 1;
			seek(DAT,0,0);
			print DAT $kai;
			close(DAT);
			
			if ($kai >= $cf{max_failpass}) {
				rename("$cf{datadir}/pwd/$in{id}.dat","$cf{datadir}/pwd/$in{id}.lock");
				auth_err("一定回数以上間違ったログインをしたためロックしました");
			}
			
			auth_err("認証できません");
		}
		
		# ロックファイルを開放しておく
		unlink("$cf{datadir}/pwd/$in{id}.dat") if (-e "$cf{datadir}/pwd/$in{id}.dat");
		
		# 新規セッション発行
		my $ses = new CGI::Session(undef,undef,{Directory => "$cf{datadir}/ses"}) or die CGI::Session->errstr;
		
		# 有効時間は1時間
		$ses->expire(3600);
		
		# セッションID
		my $sid = $ses->id();
		$in{sid} = $sid;
		
		# 掃除
		ses_clean();
	
	# 入室画面
	} elsif ($in{sid} eq '') {
		enter_form();
	
	# 認証
	} else {
		# セッション認識
		my $ses = CGI::Session->load(undef,$in{sid},{Directory => "$cf{datadir}/ses"});
		
		# ログアウト
		if ($in{logoff}) {
			$ses->delete();
			
			# 入室画面に戻る
			if ($ENV{PERLXS} eq "PerlIS") {
				print "HTTP/1.0 302 Temporary Redirection\r\n";
				print "Content-type: text/html\n";
			}
			print "Location: $cf{admin_cgi}\n\n";
			exit;
		}
		
		# 期限切れ
		if ( $ses->is_expired or $ses->is_empty ) {
			my $data = qq|<p>[<a href="$cf{admin_cgi}">ログインする</a>]</p>|;
			auth_err("タイムアウトです。再度ログインしてください。$data");
   		}
	}
}

#-----------------------------------------------------------
#  入室画面
#-----------------------------------------------------------
sub enter_form {
	header("入室画面");
	print <<EOM;
<div id="body">
<form action="$cf{admin_cgi}" method="post">
<fieldset id="login">
<legend> Log in </legend>
<p>
	username<br>
	<input type="text" name="id" class="auth">
</p><p>
	password<br>
	<input type="password" name="pw" class="auth">
</p>
<div class="ta-r">
	<input type="submit" name="login" value="Log in">
</div>
</fieldset>
</form>
<script>self.document.forms[0].id.focus();</script>
</body>
</div>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  パスワード管理
#-----------------------------------------------------------
sub pass_mgr {
	# 追加
	if ($in{add} && $in{id} ne '' && $in{pw} ne '') {
		if ($in{id} =~ /\W/ or $in{pw} =~ /\W/) {
			error("ID又はパスワードに英数字・アンダーバー以外が含まれています");
		}
		# 暗号化
		my $crypt = encrypt($in{pw});
		
		my ($flg,@log);
		open(DAT,"+< $cf{datadir}/pass.dat");
		while(<DAT>) {
			my ($id,$pw) = split(/\t/);
			
			# ID重複
			if ($in{id} eq $id) {
				$flg++;
				last;
			}
			push(@log,$_);
		}
		if ($flg) {
			close(DAT);
			error("このIDはすでに作成されてます");
		}
		push(@log,"$in{id}\t$crypt\n");
		seek(DAT,0,0);
		print DAT @log;
		truncate(DAT,tell(DAT));
		close(DAT);
	}
	
	my ($chg,$del);
	for ( keys %in ) {
		if (/^chg:(\w+)/) {
			$chg = $1;
			last;
		} elsif (/^del:(\w+)/) {
			$del = $1;
			last;
		}
	}
	# パス変更
	if ($chg) {
		if ($in{"pwd:$chg"} eq '') {
			error("パスワードが未入力です");
		} elsif ($in{"pwd:$chg"} =~ /\W/) {
			error("パスワードに英数字・アンダーバー以外が含まれています");
		}
		
		# 暗号化
		my $crypt = encrypt($in{"pwd:$chg"});
		
		my @log;
		open(DAT,"+< $cf{datadir}/pass.dat");
		while(<DAT>) {
			my ($id,$pw) = split(/\t/);
			
			if ($chg eq $id) {
				$_ = "$id\t$crypt\n";
			}
			push(@log,$_);
		}
		seek(DAT,0,0);
		print DAT @log;
		truncate(DAT,tell(DAT));
		close(DAT);
		
		pwd_msg("パスワードを変更しました");
	
	# 削除
	} elsif ($del) {
		my @log;
		open(DAT,"+< $cf{datadir}/pass.dat");
		while(<DAT>) {
			my ($id,$pw) = split(/\t/);
			next if ($del eq $id);
			
			push(@log,$_);
		}
		seek(DAT,0,0);
		print DAT @log;
		truncate(DAT,tell(DAT));
		close(DAT);
	}
	
	# 画面表示
	header("パスワード管理");
	print <<EOM;
<div id="body">
<div class="back-btn">
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="sid" value="$in{sid}">
<input type="submit" value="&lt; メニュー">
</form>
</div>
<div class="ttl">■ 管理パスワード管理</div>
<form action="$cf{admin_cgi}" method="post" name="selform">
<input type="hidden" name="sid" value="$in{sid}">
<input type="hidden" name="pass_mgr" value="1">
<p>
	・ 新規作成・削除・変更を行います。<br>
	・ ID及びパスワードで使用できる文字は「英数字及びアンダーバー」のみ。
</p>
<table class="form-tbl">
<tr>
	<th class="ta-c"></th>
	<th class="ta-c">ログインID</th>
	<th class="ta-c">パスワード</th>
</tr><tr>
	<td>[新規]</td>
	<td><input type="text" name="id" size="20"></td>
	<td>
		<input type="text" name="pw" size="20">
		<input type="submit" name="add" value="追加">
	</td>
</tr>
EOM

	open(IN,"$cf{datadir}/pass.dat");
	while(<IN>) {
		my ($id,$pw) = split(/\t/);
		
		print qq|<tr><td><input type="submit" name="del:$id" value="削除" onclick="return confirm('よろしいですか？');"></td>|;
		print qq|<td class="ta-c"><b>$id</b></td>|;
		print qq|<td><input type="text" name="pwd:$id" size="20">\n|;
		print qq|<input type="submit" name="chg:$id" value="変更"></td></tr>\n|;
	}
	close(IN);
	
	print <<EOM;
</table>
</form>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  メッセージ
#-----------------------------------------------------------
sub pwd_msg {
	my $msg = shift;
	
	header($msg);
	print <<EOM;
<div id="body">
<div id="msg-box">
	<p>$msg</p>
	<p>
		<form action="$cf{admin_cgi}" method="post">
		<input type="hidden" name="pass_mgr" value="1">
		<input type="hidden" name="sid" value="$in{sid}">
		<input type="submit" value="最初の画面へ戻る">
		</form>
	</p>
</div>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  認証エラー
#-----------------------------------------------------------
sub auth_err {
	my $msg = shift;
	
	header("認証エラー");
	print <<EOM;
<div id="body">
<div id="err-box">
	<h4>ERROR!</h4>
	<p id="err-msg">$msg</p>
	<p><input type="button" value="入力画面へ戻る" onclick="window.open('$cf{admin_cgi}','_self')"></p>
</div>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  セッションディレクトリ掃除
#-----------------------------------------------------------
sub ses_clean {
	my $time = time;
	
	opendir(DIR,"$cf{datadir}/ses");
	while( my $dir = readdir(DIR) ) {
		next if ($dir eq '.');
		next if ($dir eq '..');
		next if ($dir eq 'index.html');
		
		# ファイル時間取得
		my $mtime = (stat("$cf{datadir}/ses/$dir"))[9];
		
		# 1時間以上経過しているファイルは削除
		unlink("$cf{datadir}/ses/$dir") if ($time - $mtime > 3600);
	}
	closedir(DIR);
}

#-----------------------------------------------------------
#  Digest::SHA256 暗号
#-----------------------------------------------------------
sub encrypt {
	my $plain = shift;
	
	my @str = ('a' .. 'z', 'A' .. 'Z', 0 .. 9);
	my $salt; 
	for (1 .. 8) { $salt .= $str[int(rand(@str))]; }
	
	# 変換
	return $salt . sha256_base64($salt . $plain);
}

#-----------------------------------------------------------
#  Digest::SHA256 照合
#-----------------------------------------------------------
sub decrypt {
	my ($crypt,$plain) = @_;
	
	# 照合
	my $salt = substr($crypt,0,8);
	return $crypt eq ($salt . sha256_base64($salt . $plain)) ? 1 : 0;
}


1;

