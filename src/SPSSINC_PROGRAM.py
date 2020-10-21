#/***********************************************************************
# * Licensed Materials - Property of IBM 
# *
# * IBM SPSS Products: Statistics Common
# *
# * (C) Copyright IBM Corp. 1989, 2020
# *
# * US Government Users Restricted Rights - Use, duplication or disclosure
# * restricted by GSA ADP Schedule Contract with IBM Corp. 
# ************************************************************************/

# Extension command for running arbitrary programs without the need to
# turn them into extension commands

# Usage:
# SPSSINC PROGRAM programname arguments [/help].
# where programname is of the form modulename.functionname or, if already defined,
# it can be just the functionname.
#
# arguments is arbitrary and will be passed to the specified function in sys.argv
# mimicing the general Python command-line argument mechansm.
# The arguments are passed as tokenized by the SPSS Universal Parser.
# The main implication of this is that  text like method=least-squares will appear
# in the argument list as ['method', '=', 'least', '-', 'squares']
# unless it is all quoted, regardless of whether or not it is written with spaces
# Example:
# SPSSINC PROGRAM testpgm.mypgn a b c=100.
# testpgm.mypgm:
#import spss, sys
#def mypgm():
    #print sys.argv
#produces
#[testpgm.mypgm. 'a', 'b', 'c', '=', '100']

# The Python optparse module may be helpful in parsing these options

# Note that Python built-in functions are not supported, because this 
# mechanism does not provide for return values and because those functions
# do not use sys.argv.

# Exceptions are captured and turned into a Warnings pivot table.
# /help causes generic help text to be displayed, and the specified program
# is not called.

__author__  =  'spss, jkp'
__version__ =  '1.0.2'
version = __version__

# history
# 03-feb-2010 Original version

helptext = """SPSSINC PROGRAM programname arguments
where programname is of the form modulename.functionname or, if already defined,
it can be just the functionname.  Note that modulename and functionname are case
sensitive.

The argument values depend on the particular program being run.  Consult the documentation
for the particular program to find the specifications.  A typical example might look like this.

SPSSINC PROGRAM testpgm.mypgn x=age y = income z=.05.
"""

import spss, sys

def Run(args):

    #enable localization
    global _
    try:
        _("---")
    except:
        def _(msg):
            return msg
    if "HELP" in args[list(args.keys())[0]]:
        #print helptext
        helper()
        return
    try:
        try:
            args = args[list(args.keys())[0]][''][0]['TOKENLIST']
            pgm = args[0]
        except:
            raise ValueError("The name of the program to run must be the first parameter of the command, but no parameters were given")
        
        sys.argv = args
        pgmlist = pgm.split(".")
        if len(pgmlist) > 1:      # command names a module containing the function
            pgmstr = ".".join(pgmlist[0:-1])
            try:
                exec("import " + pgmstr )
            except:
                raise ImportError("The specified program was not found or could not be loaded: %s" % pgm)
            exec(pgm+"()")
        else:
            loadedfunc = getattr(sys.modules["__main__"], pgm, None)
            modname = "__main__"
            if not callable(loadedfunc):
                raise ValueError("""The specified function or class was given without a module name but is not defined: %s""" % pgm)
            loadedfunc()
    except:
        warnings = NonProcPivotTable("Warnings",tabletitle=_("Warnings "))
        msg = sys.exc_info()[1]
        if _isseq(msg):
            msg = ",".join(
                [
                    (isinstance(item, (float, int)) or item is None)
                    and str(item)
                    or item
                    for item in msg
                ]
            )
        if msg is None:  # no message with exception # Python3 change
            msg = str(sys.exc_info()[0])  # if no message, use the type of the exception (ugly)
        warnings.addrow(str(msg))
        warnings.generate()

def helper():
    """open html help in default browser window
    
    The location is computed from the current module name"""
    
    import webbrowser, os.path
    
    path = os.path.splitext(__file__)[0]
    helpspec = "file://" + path + os.path.sep + \
         "markdown.html"
    
    # webbrowser.open seems not to work well
    browser = webbrowser.get()
    if not browser.open_new(helpspec):
        print(("Help file not found:" + helpspec))
try:    #override
    from extension import helper
except:
    pass        
class NonProcPivotTable(object):
    """Accumulate an object that can be turned into a basic pivot table once a procedure state can be established"""
    
    def __init__(self, omssubtype, outlinetitle="", tabletitle="", caption="", rowdim="", coldim="", columnlabels=[],
                 procname="Messages"):
        """omssubtype is the OMS table subtype.
        caption is the table caption.
        tabletitle is the table title.
        columnlabels is a sequence of column labels.
        If columnlabels is empty, this is treated as a one-column table, and the rowlabels are used as the values with
        the label column hidden
        
        procname is the procedure name.  It must not be translated."""
        
        attributesFromDict(locals())
        self.rowlabels = []
        self.columnvalues = []
        self.rowcount = 0

    def addrow(self, rowlabel=None, cvalues=None):
        """Append a row labelled rowlabel to the table and set value(s) from cvalues.
        
        rowlabel is a label for the stub.
        cvalues is a sequence of values with the same number of values are there are columns in the table."""

        if cvalues is None:
            cvalues = []
        self.rowcount += 1
        if rowlabel is None:
            self.rowlabels.append(str(self.rowcount))
        else:
            self.rowlabels.append(rowlabel)
        self.columnvalues.extend(cvalues)
        
    def generate(self):
        """Produce the table assuming that a procedure state is now in effect if it has any rows."""
        
        privateproc = False
        if self.rowcount > 0:
            try:
                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
            except:
                spss.StartProcedure(self.procname)
                privateproc = True
                table = spss.BasePivotTable(self.tabletitle, self.omssubtype)
            if self.caption:
                table.Caption(self.caption)
            if self.columnlabels != []:
                table.SimplePivotTable(self.rowdim, self.rowlabels, self.coldim, self.columnlabels, self.columnvalues)
            else:
                table.Append(spss.Dimension.Place.row,"rowdim",hideName=True,hideLabels=True)
                table.Append(spss.Dimension.Place.column,"coldim",hideName=True,hideLabels=True)
                colcat = spss.CellText.String("Message")
                for r in self.rowlabels:
                    cellr = spss.CellText.String(r)
                    table[(cellr, colcat)] = cellr
            if privateproc:
                spss.EndProcedure()
                
def attributesFromDict(d):
    """build self attributes from a dictionary d."""
    self = d.pop('self')
    for name, value in d.items():
        setattr(self, name, value)
        
def _isseq(obj):
    """Return True if obj is a sequence, i.e., is iterable.

    Will be False if obj is a string, Unicode string, or basic data type"""

    # differs from operator.isSequenceType() in being False for a string

    if isinstance(obj, str):
        return False
    else:
        try:
            iter(obj)
        except:
            return False
        return True

