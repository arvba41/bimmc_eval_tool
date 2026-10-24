\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{PCIM-Abstract}[2026/05/07]

\LoadClass[onecolumn,11pt,a4paper]{article}

%set page margins
\RequirePackage{geometry}
\geometry{left=1.7cm,right=1.7cm,top=2.2cm,bottom=3.0cm}

%column sep
\setlength\columnsep{1.5em}

%locale
\RequirePackage[english]{babel}
\PassOptionsToPackage{USenglish}{babel}
\RequirePackage{csquotes}

%set Arial style font
\RequirePackage{helvet}
\renewcommand{\familydefault}{\sfdefault}
\renewcommand{\ttfamily}{\sffamily}
\RequirePackage{microtype}
\RequirePackage{textgreek}

\RequirePackage{amsmath}

%paragraph spacing
\parskip=6pt plus 2pt
\parindent=0pt

%author & affiliation
\RequirePackage{authblk}
\renewcommand*{\Affilfont}{\! \normalfont}
\renewcommand\Authsep{, }
\renewcommand\Authand{, }
\renewcommand\Authands{, }

%Topic
\newcommand{\topicnumberandnames}[1]{\gdef\@topicnumberandnames{#1}}
\newcommand{\presentationform}[1]{\gdef\@presentationform{#1}}
\renewcommand{\abstract}[1]{\gdef\@abstract{#1}}

%title
\usepackage{tabto}
\def\@maketitle{%
\newpage
\null
{\bfseries\fontsize{16}{19.2}\selectfont \@title \par}%
\vskip 1.5em%
{\large \@topicnumberandnames\\
Preferred presentation form: \@presentationform \par}
\par
\vskip 1.5em
\section*{Abstract}
\@abstract\par
\vskip 1.5em%
}

\newcommand{\printtitle}{\maketitle\suppressfloats} %no floats on first column

%set font size explicitly for headings
\RequirePackage{titlesec}
%section
\DeclareFixedFont{\sectfont}{OT1}{\familydefault}{b}{n}{14}
\titleformat*{\section}{\sectfont}
\titlespacing*{\section}{0pt}{1em plus .5em minus .5em}{.5em}
%subsection
\DeclareFixedFont{\subsectfont}{OT1}{\familydefault}{b}{n}{12}
\titleformat*{\subsection}{\subsectfont}
\titlespacing*{\subsection}{0pt}{.5em plus .25em minus .25em}{.25em}
%subsubsection
\DeclareFixedFont{\subsubsectfont}{OT1}{\familydefault}{b}{n}{11}
\titleformat*{\subsubsection}{\subsubsectfont}
\titlespacing*{\subsubsection}{0pt}{.25em plus .125em minus .125em}{.125em}
%set footnotes with 10 pt
\DeclareFixedFont{\footnotefont}{OT1}{\familydefault}{m}{n}{10}
\renewcommand{\footnotesize}{\footnotefont}

%graphics
\RequirePackage{graphicx}

%Figure captions
\RequirePackage{caption}
\captionsetup[table]{format=hang,justification=justified,singlelinecheck=false,labelfont={sf,bf},font=small,labelsep=colon,position=top,name={Tab.}}
\captionsetup[figure]{format=hang,justification=justified,singlelinecheck=false,labelfont={sf,bf},font=small,aboveskip=5pt,labelsep=colon,name={Fig.}}
\RequirePackage[caption=false,font=footnotesize,labelfont=sf,singlelinecheck=true]{subfig}

%reference
\RequirePackage{cleveref}
\Crefname{equation}{Equation}{Equations}
\Crefname{figure}{Figure}{Figures}
\Crefname{tabular}{Table}{Tables}
\crefname{equation}{Eq.}{Eqs.}
\crefname{figure}{Fig.}{Figs.}
\crefname{tabular}{Tab.}{Tabs.}

%lists
\renewcommand\labelitemi{--}

%units
\RequirePackage{siunitx}
\sisetup{detect-mode,detect-weight}

%bibliography
\usepackage[style=ieee,backend=biber,doi=true,isbn=false,url=false,minnames=5,maxnames=6]{biblatex}
%\defbibheading{bibliography}[\refname]{\section{References}}%number references
\renewcommand{\mkbibacro}[1]{#1}