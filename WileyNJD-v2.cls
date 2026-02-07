\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{WileyNJD-v2}[2026/02/07 Local fallback class for reproducible manuscript builds]

% Ignore proprietary Wiley options if present.
\DeclareOption*{}
\ProcessOptions\relax
\LoadClass[11pt]{article}

\RequirePackage[T1]{fontenc}
\RequirePackage[utf8]{inputenc}
\RequirePackage{lmodern}
\RequirePackage[margin=1in]{geometry}
\RequirePackage{amsmath,amssymb,amsthm}
\RequirePackage{bm}
\RequirePackage{graphicx}
\newenvironment{measuredfigure}{}{}
\newenvironment{measuredtable}{}{}
\RequirePackage{xcolor}
\RequirePackage{booktabs}
\RequirePackage{multirow}
\RequirePackage{threeparttable}
\RequirePackage{algorithm}
\RequirePackage{algorithmic}
\RequirePackage{float}
\RequirePackage{subcaption}
\RequirePackage{natbib}
\setkeys{Gin}{draft}

\makeatletter
\newcommand{\@wtitle}{}
\newcommand{\@wauthors}{}
\newcommand{\@waddresses}{}
\newcommand{\@wabstract}{}
\newcommand{\@wkeywords}{}
\newcommand{\@wcorres}{}
\newcommand{\@wpresentaddress}{}

\renewcommand{\title}[2][]{\gdef\@wtitle{#2}}
\renewcommand{\author}[2][]{%
  \ifx\@wauthors\@empty
    \gdef\@wauthors{#2}%
  \else
    \g@addto@macro\@wauthors{\par #2}%
  \fi
}
\newcommand{\address}[2][]{%
  \ifx\@waddresses\@empty
    \gdef\@waddresses{#2}%
  \else
    \g@addto@macro\@waddresses{\par #2}%
  \fi
}
\renewcommand{\abstract}[2][]{\gdef\@wabstract{#2}}
\newcommand{\keywords}[1]{\gdef\@wkeywords{#1}}
\newcommand{\corres}[1]{\gdef\@wcorres{#1}}
\newcommand{\presentaddress}[1]{\gdef\@wpresentaddress{#1}}

\renewcommand{\maketitle}{%
  \begin{center}
    {\LARGE\bfseries \@wtitle\par}
    \vspace{1em}
    {\large \@wauthors\par}
    \vspace{0.5em}
    {\small \@waddresses\par}
  \end{center}
  \ifx\@wcorres\@empty\else
    \noindent\textbf{Correspondence: }\@wcorres\par
  \fi
  \ifx\@wpresentaddress\@empty\else
    \noindent\textbf{Present address: }\@wpresentaddress\par
  \fi
  \ifx\@wabstract\@empty\else
    \section*{Summary}
    \@wabstract\par
  \fi
  \ifx\@wkeywords\@empty\else
    \noindent\textbf{Keywords: }\@wkeywords\par
  \fi
  \vspace{1em}
}
\makeatother

% Wiley-front-matter compatibility commands.
\newcommand{\articletype}[1]{}
\newcommand{\received}[1]{}
\newcommand{\revised}[1]{}
\newcommand{\accepted}[1]{}
\newcommand{\copyyear}[1]{}
\newcommand{\startpage}[1]{}
\newcommand{\authormark}[1]{}
\newcommand{\jnlcitation}[1]{}
\newcommand{\orgdiv}[1]{#1}
\newcommand{\orgname}[1]{#1}
\newcommand{\orgaddress}[1]{#1}
\newcommand{\state}[1]{#1}
\newcommand{\country}[1]{#1}
\newcommand{\email}[1]{\texttt{#1}}
\newcommand{\cname}[1]{#1}
\newcommand{\cyear}[1]{#1}
\newcommand{\ctitle}[1]{#1}
\newcommand{\cjournal}[1]{#1}
\newcommand{\cvol}[1]{#1}

\newenvironment{biography}[2]{\par\noindent\textbf{#2} }{\par}

% Provide algorithmicx-style command names via algorithmic package.
\newcommand{\State}{\STATE}
\newcommand{\For}{\FOR}
\newcommand{\EndFor}{\ENDFOR}
\newcommand{\While}{\WHILE}
\newcommand{\EndWhile}{\ENDWHILE}
\newcommand{\If}{\IF}
\newcommand{\Else}{\ELSE}
\newcommand{\EndIf}{\ENDIF}

% Keep fallback builds deterministic on minimal TeX installations.
\AtBeginDocument{%
  \nofiles
  \bibliographystyle{plainnat}%
}
