#!/usr/local/bin/perl

#┌─────────────────────────────────
#│ CLIP MAIL : check.cgi - 2021/02/13
#│ copyright (c) KentWeb, 1997-2022
#│ https://www.kent-web.com/
#└─────────────────────────────────

# モジュール宣言
use strict;
use CGI::Carp qw(fatalsToBrowser);
use lib './lib';

# 外部ファイル取り込み
require './init.cgi';
my %cf = set_init();

print <<EOM;
Content-type: text/html; charset=$cf{charset}

<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>Check Mode</title>
</head>
<body>
<b>Check Mode: [ $cf{version} ]</b>
<ul>
<li>Perlバージョン : $]
EOM

# sendmailチェック
print "<li>sendmailパス : ";
if (-e $cf{sendmail}) {
	print "OK\n";
} else {
	print "NG → $cf{sendmail}\n";
}

# ディレクトリ
for ( $cf{datadir}, "$cf{datadir}/ses", "$cf{datadir}/pwd", $cf{upldir} ) {
	if (-d $_) {
		print "<li>$_ ディレクトリパス : OK\n";
		
		if (-r $_ && -w $_ && -x $_) {
			print "<li>$_ ディレクトリパーミッション : OK\n";
		} else {
			print "<li>$_ ディレクトリパーミッション : NG\n";
		}
	} else {
		print "<li>$_ ディレクトリパス : NG\n";
	}
}

# ファイルチェック
for (qw(log.cgi ses.cgi pass.dat)) {
	if (-f "$cf{datadir}/$_") {
		print "<li>$cf{datadir}/$_ ファイルパス : OK\n";
		
		if (-r "$cf{datadir}/$_" && -w "$cf{datadir}/$_") {
			print "<li>$_ ファイルパーミッション : OK\n";
		} else {
			print "<li>$_ ファイルパーミッション : NG\n";
		}
	} else {
		print "<li>$_ ファイルパス : NG\n";
	}
}

# テンプレート
for (qw(conf.html error.html thanks.html mail.txt reply.txt)) {
	print "<li>テンプレートパス ( $_ ) : ";
	
	if (-f "$cf{tmpldir}/$_") {
		print "OK\n";
	} else {
		print "NG\n";
	}
}

print <<EOM;
</ul>
</body>
</html>
EOM
exit;


