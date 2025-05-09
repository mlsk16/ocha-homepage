#!/usr/local/bin/perl

#┌─────────────────────────────────
#│ Clip Mail : admin.cgi - 2021/02/13
#│ copyright (c) kentweb, 1997-2022
#│ https://www.kent-web.com/
#└─────────────────────────────────

# モジュール実行
use strict;
use CGI::Carp qw(fatalsToBrowser);
use vars qw(%in %cf);
use lib './lib';
use CGI::Minimal;
use CGI::Session;
use Digest::SHA::PurePerl qw(sha256_base64);

# 外部ファイル取り込み
require './init.cgi';
%cf = set_init();

# データ受理
CGI::Minimal::max_read_size($cf{maxdata});
my $cgi = CGI::Minimal->new;
error('容量オーバー') if ($cgi->truncated);

# フォームデコード
%in = parse_form();

# 認証
require "./lib/login.pl";
auth_login();

# 処理分岐
if ($in{down_log}) { down_log(); }
if ($in{pass_mgr}) { pass_mgr(); }

# メニュー画面
menu_html();

#-----------------------------------------------------------
#  メニュー画面
#-----------------------------------------------------------
sub menu_html {
	header("メニューTOP");
	print <<EOM;
<div id="body">
<p>選択ボタンを押してください。</p>
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="sid" value="$in{sid}">
<table class="form-tbl">
<tr>
	<th>選択</th>
	<th width="280">処理メニュー</th>
</tr><tr>
	<td><input type="submit" name="down_log" value="選択"></td>
	<td>ログデータ取得</td>
</tr><tr>
	<td><input type="submit" name="pass_mgr" value="選択"></td>
	<td>パスワード管理</td>
</tr><tr>
	<td><input type="submit" name="logoff" value="選択"></td>
	<td>ログアウト</td>
</tr>
</table>
</form>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  ログダウンロード
#-----------------------------------------------------------
sub down_log {
	# ダウンロード実行
	if ($in{downld}) {
		# 選択チェック
		if (!$in{br}) { error("オプションに未選択があります"); }
		
		# 改行コード定義
		my %br = ( win => "\r\n", mac => "\r", unix => "\n" );
		
		# ログをオープン
		my ($i,@item,%key,%head,%csv);
		open(IN,"$cf{datadir}/log.cgi") or error("open err: log.cgi");
		while(<IN>) {
			chomp;
			$i++;
			my @log = split(/<>/);
			
			my $csv;
			foreach my $n (0 .. $#log) {
				my ($key,$val) = split(/=/,$log[$n]);
				
				if ($n <= 1) {
					$head{$i} .= "$val,";
					next;
				}
				
				if (!defined $key{$key}) {
					$key{$key}++;
					push(@item,$key);
				}
				
				# HTML変換
				$val =~ s/&lt;/</g;
				$val =~ s/&gt;/>/g;
				$val =~ s/&quot;/"/g;
				$val =~ s/&#39;/'/g;
				$val =~ s/&amp;/&/g;
				
				$csv{"$i<>$key"} = $val;
			}
		}
		close(IN);
		
		# ダウンロード用ヘッダー
		print "Content-type: application/octet-stream\n";
		print "Content-Disposition: attachment; filename=data.csv\n\n";
		binmode(STDOUT);
		
		# 項目
		print qq|Date,IP,|, join(',', @item), $br{$in{br}};
		
		# CSV
		foreach (1 .. $i) {
			my $csv;
			foreach my $key (@item) {
				$csv .= qq|$csv{"$_<>$key"},|;
			}
			$csv =~ s/,$//;
			
			print "$head{$_}$csv$br{$in{br}}";
		}
		exit;
	}
	
	# ログ個数を数える
	my $i = 0;
	open(IN,"$cf{datadir}/log.cgi");
	++$i while(<IN>);
	close(IN);
	
	# ダウンロード画面
	header("CSVダウンロード");
	print <<EOM;
<div class="back-btn">
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="sid" value="$in{sid}">
<input type="submit" value="&lt; メニュー">
</form>
</div>
<div id="body">
・ 現在のログ個数： <b>$i</b>個<br>
・ 改行形式を選択して、ダウンロードボタンを押してください。<br>
<form action="$cf{admin_cgi}" method="post">
<input type="hidden" name="sid" value="$in{sid}">
<input type="hidden" name="down_log" value="1">
<table class="form-tbl">
<tr>
	<th>改行形式</th>
	<td>
		<input type="radio" name="br" value="win">Windows形式 （CR+LF）<br>
		<input type="radio" name="br" value="unix">Macintosh/UNIX形式 （LF）<br>
		<input type="radio" name="br" value="mac">Macintosh旧形式 （CR）<br>
	</td>
</tr>
</table>
<input type="submit" name="downld" value="ダウンロード">
</form>
</div>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  HTMLヘッダ
#-----------------------------------------------------------
sub header {
	my $ttl = shift;
	
	print <<EOM;
Content-type: text/html; charset=utf-8

<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<link href="$cf{cmnurl}/admin.css" rel="stylesheet">
<title>$ttl</title>
</head>
<div id="head">
	Clipmail 管理画面 ::
</div>
EOM
}

#-----------------------------------------------------------
#  エラー処理
#-----------------------------------------------------------
sub error {
	my $err = shift;
	
	header("ERROR");
	print <<EOM;
<h3>ERROR !</h3>
<p class="red">$err<p>
<p><input type="button" value="前画面に戻る" onclick="history.back()"></p>
</body>
</html>
EOM
	exit;
}

#-----------------------------------------------------------
#  フォームデコード
#-----------------------------------------------------------
sub parse_form {
	my %in;
	foreach ( $cgi->param() ) {
		my $val = $cgi->param($_);
		
		$val =~ s/&/&amp;/g;
		$val =~ s/</&lt;/g;
		$val =~ s/>/&gt;/g;
		$val =~ s/"/&quot;/g;
		$val =~ s/'/&#39;/g;
		$val =~ s/[\r\n]/\t/g;
		
		$in{$_} = $val;
	}
	return %in;
}

